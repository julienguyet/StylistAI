import mlflow
import io
import pandas as pd
import numpy as np
import ast
from itertools import chain
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
import warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
pd.options.mode.chained_assignment = None
warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import tensorflow as tf
import tensorflow_recommenders as tfrs

DASHLINE = "---" * 15
RANDOM_SEED = 42
TRAIN_SPLIT = 0.8
SHUFFLE_BUFFER = 100_000
MAX_HISTORY = 50
BATCH_SIZE = 1024  # Back to original - larger batches are actually better for retrieval

# ------------- Model hyperparameters ------------- #
EPOCHS = 100
LEARNING_RATE = 1e-3  # Back to original
EMBEDDINGS_REGULARIZER = tf.keras.regularizers.L2(l2=1e-4)  # Light regularization

# Customer Tower
CUSTOMER_EMBEDDING_DIM = 64
CLUB_EMBEDDING_DIM = 32
NEWS_EMBEDDING_DIM = 16
SALES_EMBEDDING_DIM = 16

# Article Tower
ARTICLE_EMBEDDING_DIM = 64
PRODUCT_TYPE_EMBEDDING_DIM = 32
SECTION_EMBEDDING_DIM = 16
PRODUCT_GROUP_EMBEDDING_DIM = 16
DESC_EMBEDDING_DIM = 64

# MLP Layers
MLP_LAYER_1 = 128
MLP_LAYER_2 = 64
MLP_DROPOUT = 0.2  # Light dropout
DENSE_REGULARIZER = tf.keras.regularizers.L2(l2=1e-4)  # Consistent with embeddings

# Text vectorization settings
DESC_MAX_TOKENS = 10_000
DESC_OUTPUT_SEQ_LEN = 30

print("Starting Job: Training a Two Tower Model with TF Recommenders")
print(DASHLINE)

# ------------- Load and Prepare Data ------------- #
print("Loading Customers, Stores and Articles Info...")
customers_csv_path = '/data/processed/customers_df.csv'
stores_csv = '/data/processed/stores_df.csv'
articles_csv = '/data/processed/articles_df.csv'
customers_df = pd.read_csv(customers_csv_path)
stores_df = pd.read_csv(stores_csv)
stores_df.drop(columns=['Unnamed: 0'], inplace=True)
stores_loc = stores_df[['country', 'state', 'postal_code']]
stores_loc.dropna(inplace=True)
stores_loc.reset_index(drop=True, inplace=True)
customers_data = pd.merge(customers_df, stores_loc, on='postal_code')
customers_data = customers_data.loc[customers_data['country'].isin(['Portugal'])]
customers_data.reset_index(drop=True, inplace=True)
customers_data.fillna({'favorite_sales_channel': 'UNKNOWN'}, inplace=True)
customers_data['favorite_sales_channel'] = customers_data['favorite_sales_channel'].astype(str)
customers_data['purchased_articles'] = customers_data['purchased_articles'].apply(lambda x: (ast.literal_eval(x)))
customers_data['nb_past_purchases'] = customers_data['purchased_articles'].apply(lambda x: len(x))
customers_data['nb_past_purchases'].mean().round(0)
all_articles = set(chain.from_iterable(customers_data["purchased_articles"]))
articles_df = pd.read_csv(articles_csv)
print("Main information processed and ready for training dataset crafting!")
print(DASHLINE)

# ------------- Scale Data ------------- #
print("Scaling Age Column...")
scaler_path = "/data/scalers/age_scaler_portugal.pkl"
scaler = MinMaxScaler()
scaler.fit(customers_data[["age"]])
customers_data["age_scaled"] = scaler.transform(customers_data[["age"]])
joblib.dump(scaler, scaler_path)
print(f"Data scaled and Scaler saved at: {scaler_path}")
print(DASHLINE)

# ------------- Feature Engineering on Purchase History ------------- #
print("Now moving to Interaction Dataset...")

def _ensure_list(x):
    if isinstance(x, list):
        return x
    if pd.isna(x):
        return []
    try:
        return ast.literal_eval(x)
    except (ValueError, SyntaxError):
        s = str(x).strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        return [i.strip().strip("'").strip("'") for i in s.split(",") if i.strip()]

def _pad_or_truncate(items, max_len=MAX_HISTORY):
    items = list(items)[:max_len]
    if len(items) < max_len:
        items = items + [""] * (max_len - len(items))
    return items

def _remove_target_from_history(row):
    """Remove the target article from purchase history to prevent leakage"""
    history = _ensure_list(row["purchased_articles"]).copy()
    target = row["article_id"]
    history = [item for item in history if item != target]
    return _pad_or_truncate(history)

customers_data["purchased_articles_list"] = customers_data["purchased_articles"].apply(_ensure_list)

interactions = customers_data[["customer_id", "purchased_articles", "purchased_articles_list"]].explode("purchased_articles_list")
interactions = interactions.dropna(subset=["purchased_articles_list"])
interactions = interactions[interactions["purchased_articles_list"] != ""]
interactions = interactions.rename(columns={"purchased_articles_list": "article_id"})
interactions["history_article_ids"] = interactions.apply(_remove_target_from_history, axis=1)

# Bring in customer and article features used by the model
customer_features = customers_data[
    [
        "customer_id",
        "age_scaled",
        "club_member_status",
        "fashion_news_frequency",
        "favorite_sales_channel",
    ]
].copy()

articles_features = articles_df[["article_id", "product_type_name", "section_name", "product_group_name", "detail_desc"]].copy()

# Normalize types and fill missing text fields
customer_features["customer_id"] = customer_features["customer_id"].astype(str)
articles_features["article_id"] = articles_features["article_id"].astype(str)

for col in ["club_member_status", "fashion_news_frequency", "favorite_sales_channel"]:
    customer_features[col] = customer_features[col].astype(str).fillna("unknown")

for col in ["product_type_name", "section_name", "product_group_name", "detail_desc"]:
    articles_features[col] = articles_features[col].astype(str).fillna("unknown")

interactions["customer_id"] = interactions["customer_id"].astype(str)
interactions["article_id"] = interactions["article_id"].astype(str)
interactions = interactions.merge(customer_features, on="customer_id", how="left")
interactions = interactions.merge(articles_features, on="article_id", how="left")
print("Interaction dataframe is ready with new features about purchases history!")
print("IMPORTANT: Target articles removed from history to prevent leakage")
print(DASHLINE)

# ------------- Create Tensorflow Dataset ------------- #
print("Creating TF Dataset...")
tf.random.set_seed(RANDOM_SEED)

# Build train/test split
interactions = interactions.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)
train_size = int(TRAIN_SPLIT * len(interactions))
train_df = interactions.iloc[:train_size]
test_df = interactions.iloc[train_size:]

# Build tf.data datasets
def df_to_dataset(df):
    history_array = np.stack(df["history_article_ids"].values)
    return tf.data.Dataset.from_tensor_slices({
        "customer_id": df["customer_id"].astype(str).values,
        "age_scaled": df["age_scaled"].astype("float32").values,
        "club_member_status": df["club_member_status"].astype(str).fillna("unknown").values,
        "fashion_news_frequency": df["fashion_news_frequency"].astype(str).fillna("unknown").values,
        "favorite_sales_channel": df["favorite_sales_channel"].astype(str).fillna("unknown").values,
        "history_article_ids": history_array,
        "article_id": df["article_id"].astype(str).values,
        "product_type_name": df["product_type_name"].astype(str).fillna("unknown").values,
        "section_name": df["section_name"].astype(str).fillna("unknown").values,
        "product_group_name": df["product_group_name"].astype(str).fillna("unknown").values,
        "detail_desc": df["detail_desc"].astype(str).fillna("unknown").values,
    })

train_ds = df_to_dataset(train_df).shuffle(SHUFFLE_BUFFER, seed=RANDOM_SEED).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
test_ds = df_to_dataset(test_df).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
print("TF dataset is ready, now moving to model definition...")
print(DASHLINE)

# Vocabularies
unique_customer_ids = customer_features["customer_id"].unique().tolist()
unique_article_ids = articles_features["article_id"].unique().tolist()
unique_club_status = customer_features["club_member_status"].unique().tolist()
unique_news_freq = customer_features["fashion_news_frequency"].unique().tolist()
unique_sales_channel = customer_features["favorite_sales_channel"].unique().tolist()

unique_product_type = articles_features["product_type_name"].unique().tolist()
unique_section = articles_features["section_name"].unique().tolist()
unique_product_group = articles_features["product_group_name"].unique().tolist()

# Article embedding shared between both towers
article_lookup = tf.keras.layers.StringLookup(vocabulary=unique_article_ids, mask_token=None)
article_embedding = tf.keras.layers.Embedding(
    article_lookup.vocabulary_size(),
    ARTICLE_EMBEDDING_DIM,
    embeddings_regularizer=EMBEDDINGS_REGULARIZER
)

# Description vectorizer
desc_vectorizer = tf.keras.layers.TextVectorization(
    max_tokens=DESC_MAX_TOKENS,
    output_mode="int",
    output_sequence_length=DESC_OUTPUT_SEQ_LEN,
)
desc_vectorizer.adapt(articles_features["detail_desc"].values)

class CustomerModel(tf.keras.Model):
    def __init__(self, article_lookup, article_embedding):
        super().__init__()
        self.customer_lookup = tf.keras.layers.StringLookup(vocabulary=unique_customer_ids, mask_token=None)
        self.club_lookup = tf.keras.layers.StringLookup(vocabulary=unique_club_status, mask_token=None)
        self.news_lookup = tf.keras.layers.StringLookup(vocabulary=unique_news_freq, mask_token=None)
        self.sales_lookup = tf.keras.layers.StringLookup(vocabulary=unique_sales_channel, mask_token=None)
        self.article_history_lookup = article_lookup
        
        self.customer_embedding = tf.keras.layers.Embedding(
            self.customer_lookup.vocabulary_size(), CUSTOMER_EMBEDDING_DIM, embeddings_regularizer=EMBEDDINGS_REGULARIZER
        )
        self.club_embedding = tf.keras.layers.Embedding(
            self.club_lookup.vocabulary_size(), CLUB_EMBEDDING_DIM, embeddings_regularizer=EMBEDDINGS_REGULARIZER
        )
        self.news_embedding = tf.keras.layers.Embedding(
            self.news_lookup.vocabulary_size(), NEWS_EMBEDDING_DIM, embeddings_regularizer=EMBEDDINGS_REGULARIZER
        )
        self.sales_embedding = tf.keras.layers.Embedding(
            self.sales_lookup.vocabulary_size(), SALES_EMBEDDING_DIM, embeddings_regularizer=EMBEDDINGS_REGULARIZER
        )
        self.article_history_embedding = article_embedding
        
        # NO BATCH NORMALIZATION - it breaks retrieval models
        self.mlp = tf.keras.Sequential([
            tf.keras.layers.Dense(MLP_LAYER_1, activation="relu", kernel_regularizer=DENSE_REGULARIZER),
            tf.keras.layers.Dropout(MLP_DROPOUT),
            tf.keras.layers.Dense(MLP_LAYER_2, kernel_regularizer=DENSE_REGULARIZER),
        ])

    def call(self, features, training=False):
        age_scaled = tf.expand_dims(features["age_scaled"], -1)
        
        # Use mean pooling with masking for variable-length history
        # Create mask BEFORE lookup (mask empty strings in original data)
        mask = tf.cast(tf.not_equal(features["history_article_ids"], ""), tf.float32)
        mask = tf.expand_dims(mask, -1)
        
        history_ids = self.article_history_lookup(features["history_article_ids"])
        history_emb = self.article_history_embedding(history_ids)
        
        # Apply mask to embeddings
        history_emb = history_emb * mask
        # Avoid division by zero
        history_pooled = tf.reduce_sum(history_emb, axis=1) / (tf.reduce_sum(mask, axis=1) + 1e-9)
        
        x = tf.concat(
            [
                self.customer_embedding(self.customer_lookup(features["customer_id"])),
                age_scaled,
                self.club_embedding(self.club_lookup(features["club_member_status"])),
                self.news_embedding(self.news_lookup(features["fashion_news_frequency"])),
                self.sales_embedding(self.sales_lookup(features["favorite_sales_channel"])),
                history_pooled,
            ],
            axis=1,
        )
        return self.mlp(x, training=training)

class ArticleModel(tf.keras.Model):
    def __init__(self, article_lookup, article_embedding):
        super().__init__()
        self.article_lookup = article_lookup
        self.article_embedding = article_embedding
        
        self.product_type_lookup = tf.keras.layers.StringLookup(vocabulary=unique_product_type, mask_token=None)
        self.section_lookup = tf.keras.layers.StringLookup(vocabulary=unique_section, mask_token=None)
        self.product_group_lookup = tf.keras.layers.StringLookup(vocabulary=unique_product_group, mask_token=None)
        
        self.product_type_embedding = tf.keras.layers.Embedding(
            self.product_type_lookup.vocabulary_size(), PRODUCT_TYPE_EMBEDDING_DIM, embeddings_regularizer=EMBEDDINGS_REGULARIZER
        )
        self.section_embedding = tf.keras.layers.Embedding(
            self.section_lookup.vocabulary_size(), SECTION_EMBEDDING_DIM, embeddings_regularizer=EMBEDDINGS_REGULARIZER
        )
        self.product_group_embedding = tf.keras.layers.Embedding(
            self.product_group_lookup.vocabulary_size(), PRODUCT_GROUP_EMBEDDING_DIM, embeddings_regularizer=EMBEDDINGS_REGULARIZER
        )

        self.desc_encoder = tf.keras.Sequential(
            [
                desc_vectorizer,
                tf.keras.layers.Embedding(desc_vectorizer.vocabulary_size(), DESC_EMBEDDING_DIM,
                                        embeddings_regularizer=EMBEDDINGS_REGULARIZER),
                tf.keras.layers.GlobalAveragePooling1D(),
            ]
        )
        
        # NO BATCH NORMALIZATION - it breaks retrieval models
        self.mlp = tf.keras.Sequential([
            tf.keras.layers.Dense(MLP_LAYER_1, activation="relu", kernel_regularizer=DENSE_REGULARIZER),
            tf.keras.layers.Dropout(MLP_DROPOUT),
            tf.keras.layers.Dense(MLP_LAYER_2, kernel_regularizer=DENSE_REGULARIZER),
        ])

    def call(self, features, training=False):
        x = tf.concat(
            [
                self.article_embedding(self.article_lookup(features["article_id"])),
                self.product_type_embedding(self.product_type_lookup(features["product_type_name"])),
                self.section_embedding(self.section_lookup(features["section_name"])),
                self.product_group_embedding(self.product_group_lookup(features["product_group_name"])),
                self.desc_encoder(features["detail_desc"]),
            ],
            axis=1,
        )
        return self.mlp(x, training=training)

# Build candidate dataset for evaluation
candidate_ds = tf.data.Dataset.from_tensor_slices(
    {
        "article_id": articles_features["article_id"].values,
        "product_type_name": articles_features["product_type_name"].values,
        "section_name": articles_features["section_name"].values,
        "product_group_name": articles_features["product_group_name"].values,
        "detail_desc": articles_features["detail_desc"].values,
    }
).batch(BATCH_SIZE)

class TwoTowerModel(tfrs.Model):
    def __init__(self, customer_model, article_model):
        super().__init__()
        self.customer_model = customer_model
        self.article_model = article_model
        self.task = tfrs.tasks.Retrieval(
            metrics=tfrs.metrics.FactorizedTopK(
                candidates=candidate_ds.map(article_model)
            )
        )

    def compute_loss(self, features, training=False):
        user_embeddings = self.customer_model(features, training=training)
        item_embeddings = self.article_model(features, training=training)
        return self.task(user_embeddings, item_embeddings)

# ------------- Train with ML Flow tracking ------------- #
print("Two Tower Model defined and now ready to be compiled...")
monitor_metric = "val_factorized_top_k/top_10_categorical_accuracy"
print(f"Main Monitored Metric for training: {monitor_metric}")
print(f"Model will be trained for {EPOCHS} epochs maximum.")
print("Starting Training with ML Flow...")
print(f"You can follow training in ML Flow by running the command: mlflow server --port 5000")
print(DASHLINE)

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("recommender")
mlflow.tensorflow.autolog(log_models=False)

with mlflow.start_run() as run:
    run_id = run.info.run_id
    base_out = os.path.join("/data/models", "mlruns_outputs", run_id)
    log_dir = os.path.join(base_out, "tb")
    ckpt_path = os.path.join(base_out, "checkpoints", "best.weights.h5")
    csv_path = os.path.join(base_out, "training.csv")
    os.makedirs(os.path.dirname(ckpt_path), exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor=monitor_metric, patience=10, mode="max",
            restore_best_weights=True, verbose=1),

        tf.keras.callbacks.ReduceLROnPlateau(
            monitor=monitor_metric, mode="max", factor=0.5, patience=5,
            min_lr=1e-6, cooldown=2, verbose=1),

        tf.keras.callbacks.TensorBoard(log_dir=log_dir),

        tf.keras.callbacks.ModelCheckpoint(
            filepath=ckpt_path, monitor=monitor_metric, mode="max",
            save_weights_only=True, save_best_only=True, verbose=1),

        tf.keras.callbacks.CSVLogger(csv_path),

        tf.keras.callbacks.TerminateOnNaN(),
    ]
    
    class MLflowMetricsCallback(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            if not logs:
                return
            metrics = {k: float(v) for k, v in logs.items() if v is not None}
            mlflow.log_metrics(metrics, step=epoch)

    callbacks.append(MLflowMetricsCallback())

    model = TwoTowerModel(CustomerModel(article_lookup, article_embedding),
                        ArticleModel(article_lookup, article_embedding))
    
    # Use Adam optimizer instead of Adagrad - better for this task
    optimizer = tf.keras.optimizers.Adam(
        learning_rate=LEARNING_RATE,
        clipnorm=1.0
    )
    model.compile(optimizer=optimizer)

    # Build models by calling with real tensors to preserve string dtypes
    model.customer_model({
        "customer_id": tf.constant(["0"], dtype=tf.string),
        "age_scaled": tf.constant([0.0], dtype=tf.float32),
        "club_member_status": tf.constant(["unknown"], dtype=tf.string),
        "fashion_news_frequency": tf.constant(["unknown"], dtype=tf.string),
        "favorite_sales_channel": tf.constant(["unknown"], dtype=tf.string),
        "history_article_ids": tf.constant([[""] * MAX_HISTORY], dtype=tf.string),
    })

    model.article_model({
        "article_id": tf.constant(["0"], dtype=tf.string),
        "product_type_name": tf.constant(["unknown"], dtype=tf.string),
        "section_name": tf.constant(["unknown"], dtype=tf.string),
        "product_group_name": tf.constant(["unknown"], dtype=tf.string),
        "detail_desc": tf.constant(["unknown"], dtype=tf.string),
    })

    summary_buf = io.StringIO()
    summary_buf.write("Customer tower summary\n")
    model.customer_model.summary(print_fn=lambda x: summary_buf.write(x + "\n"))
    summary_buf.write("\nArticle tower summary\n")
    model.article_model.summary(print_fn=lambda x: summary_buf.write(x + "\n"))
    mlflow.log_text(summary_buf.getvalue(), "model_summary.txt")

    mlflow.log_params({
        "max_history": MAX_HISTORY,
        "batch_size": BATCH_SIZE,
        "train_split": TRAIN_SPLIT,
        "random_seed": RANDOM_SEED,
        "epochs": EPOCHS,
        "monitor_metric": monitor_metric,
        "optimizer": "Adam",
        "learning_rate": LEARNING_RATE,
        "gradient_clipping": 1.0,
        "customer_embedding_dim": CUSTOMER_EMBEDDING_DIM,
        "club_embedding_dim": CLUB_EMBEDDING_DIM,
        "news_embedding_dim": NEWS_EMBEDDING_DIM,
        "sales_embedding_dim": SALES_EMBEDDING_DIM,
        "article_embedding_dim": ARTICLE_EMBEDDING_DIM,
        "product_type_embedding_dim": PRODUCT_TYPE_EMBEDDING_DIM,
        "section_embedding_dim": SECTION_EMBEDDING_DIM,
        "product_group_embedding_dim": PRODUCT_GROUP_EMBEDDING_DIM,
        "desc_embedding_dim": DESC_EMBEDDING_DIM,
        "mlp_layer_1": MLP_LAYER_1,
        "mlp_layer_2": MLP_LAYER_2,
        "mlp_dropout": MLP_DROPOUT,
        "desc_max_tokens": DESC_MAX_TOKENS,
        "desc_output_seq_len": DESC_OUTPUT_SEQ_LEN,
        "unique_customer_ids": len(unique_customer_ids),
        "unique_article_ids": len(unique_article_ids),
        "unique_club_status": len(unique_club_status),
        "unique_news_freq": len(unique_news_freq),
        "unique_sales_channel": len(unique_sales_channel),
        "unique_product_type": len(unique_product_type),
        "unique_section": len(unique_section),
        "unique_product_group": len(unique_product_group),
        "desc_vocab_size": desc_vectorizer.vocabulary_size(),
        "leakage_prevention": "target_removed_from_history",
        "batch_norm": "removed_for_stability",
    })

    history = model.fit(
        train_ds,
        validation_data=test_ds,
        epochs=EPOCHS,
        callbacks=callbacks,
    )

    mlflow.log_artifact(ckpt_path, artifact_path="checkpoints")
    mlflow.log_artifact(csv_path, artifact_path="logs")
    mlflow.log_artifacts(log_dir, artifact_path="tensorboard")
    model.load_weights(ckpt_path)
    mlflow.tensorflow.log_model(model, artifact_path="model_best")
    model_path = os.path.join(base_out, "model_best")
    mlflow.tensorflow.save_model(model, path=model_path)
    best_val = max(history.history.get(monitor_metric, [-float("inf")]))
    mlflow.log_metric(f"best_{monitor_metric}", best_val)

print("Training Over! Now exiting process.")
print(DASHLINE)
