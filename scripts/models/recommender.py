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
BATCH_SIZE = 1024

# ------------- Model hyperparameters ------------- #
EPOCHS = 50
LEARNING_RATE = 0.1

# Customer Tower
CUSTOMER_EMBEDDING_DIM = 64
CLUB_EMBEDDING_DIM = 32
NEWS_EMBEDDING_DIM = 8
SALES_EMBEDDING_DIM = 8

# Article Tower
ARTICLE_EMBEDDING_DIM = 64
PRODUCT_TYPE_EMBEDDING_DIM = 32
SECTION_EMBEDDING_DIM = 8
PRODUCT_GROUP_EMBEDDING_DIM = 8
DESC_EMBEDDING_DIM = 32

# MLP Layers
MLP_LAYER_1 = 64
MLP_LAYER_2 = 32
MLP_DROPOUT = 0.2

# Text vectorization settings.
DESC_MAX_TOKENS = 10_000
DESC_OUTPUT_SEQ_LEN = 50

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
customers_data = customers_data.loc[customers_data['country'].isin(['New Zealand'])]
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
scaler_path = "/data/scalers/age_scaler.pkl"
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

customers_data["purchased_articles_list"] = customers_data["purchased_articles"].apply(_ensure_list)
customers_data["history_article_ids"] = customers_data["purchased_articles_list"].apply(_pad_or_truncate)

interactions = customers_data[["customer_id", "purchased_articles_list"]].explode("purchased_articles_list")
interactions = interactions.dropna(subset=["purchased_articles_list"])
interactions = interactions[interactions["purchased_articles_list"] != ""]
interactions = interactions.rename(columns={"purchased_articles_list": "article_id"})

# Bring in customer and article features used by the model.
customer_features = customers_data[
    [
        "customer_id",
        "age_scaled",
        "club_member_status",
        "fashion_news_frequency",
        "favorite_sales_channel",
        "history_article_ids",
    ]
].copy()

articles_features = articles_df[["article_id", "product_type_name", "section_name", "product_group_name", "detail_desc"]].copy()

# Normalize types and fill missing text fields.
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
print(DASHLINE)

# ------------- Create Tensorflow Dataset ------------- #
print("Creating TF Dataset...")
tf.random.set_seed(RANDOM_SEED)

# Build train/test split.
interactions = interactions.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)
train_size = int(TRAIN_SPLIT * len(interactions))
train_df = interactions.iloc[:train_size]
test_df = interactions.iloc[train_size:]

# Build tf.data datasets.
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

# Vocabularies.
unique_customer_ids = customer_features["customer_id"].unique()
unique_article_ids = articles_features["article_id"].unique()
unique_club_status = customer_features["club_member_status"].unique()
unique_news_freq = customer_features["fashion_news_frequency"].unique()
unique_sales_channel = customer_features["favorite_sales_channel"].unique()

unique_product_type = articles_features["product_type_name"].unique()
unique_section = articles_features["section_name"].unique()
unique_product_group = articles_features["product_group_name"].unique()

# Text vectorizer for descriptions.
desc_vectorizer = tf.keras.layers.TextVectorization(
    max_tokens=DESC_MAX_TOKENS,
    output_mode="int",
    output_sequence_length=DESC_OUTPUT_SEQ_LEN,
)
desc_vectorizer.adapt(articles_features["detail_desc"].values)

# Shared item lookup/embedding for item ids and history pooling.
article_lookup = tf.keras.layers.StringLookup(
    vocabulary=unique_article_ids, mask_token=""
)
article_embedding = tf.keras.layers.Embedding(
    article_lookup.vocabulary_size(), ARTICLE_EMBEDDING_DIM, mask_zero=True
)

# ------------- Create Recommender Model ------------- #

class CustomerModel(tf.keras.Model):
    def __init__(self, article_lookup_layer, article_embedding_layer):
        super().__init__()
        self.customer_lookup = tf.keras.layers.StringLookup(
            vocabulary=unique_customer_ids, mask_token=None
        )
        self.customer_embedding = tf.keras.layers.Embedding(
            self.customer_lookup.vocabulary_size(), CUSTOMER_EMBEDDING_DIM
        )
        self.club_lookup = tf.keras.layers.StringLookup(
            vocabulary=unique_club_status, mask_token=None
        )
        self.club_embedding = tf.keras.layers.Embedding(
            self.club_lookup.vocabulary_size(), CLUB_EMBEDDING_DIM
        )
        self.news_lookup = tf.keras.layers.StringLookup(
            vocabulary=unique_news_freq, mask_token=None
        )
        self.news_embedding = tf.keras.layers.Embedding(
            self.news_lookup.vocabulary_size(), NEWS_EMBEDDING_DIM
        )
        self.sales_lookup = tf.keras.layers.StringLookup(
            vocabulary=unique_sales_channel, mask_token=None
        )
        self.sales_embedding = tf.keras.layers.Embedding(
            self.sales_lookup.vocabulary_size(), SALES_EMBEDDING_DIM
        )
        self.history_lookup = article_lookup_layer
        self.history_embedding = article_embedding_layer
        self.history_pool = tf.keras.layers.GlobalAveragePooling1D()
        self.mlp = tf.keras.Sequential([
            tf.keras.layers.Dense(MLP_LAYER_1, activation="relu"),
            tf.keras.layers.Dropout(MLP_DROPOUT),
            tf.keras.layers.Dense(MLP_LAYER_2),
        ])

    def call(self, features):
        history_ids = self.history_lookup(features["history_article_ids"])
        history_emb = self.history_embedding(history_ids)
        history_vec = self.history_pool(history_emb)

        x = tf.concat(
            [
                self.customer_embedding(self.customer_lookup(features["customer_id"])),
                self.club_embedding(self.club_lookup(features["club_member_status"])),
                self.news_embedding(self.news_lookup(features["fashion_news_frequency"])),
                self.sales_embedding(self.sales_lookup(features["favorite_sales_channel"])),
                tf.expand_dims(features["age_scaled"], -1),
                history_vec,
            ],
            axis=1,
        )
        return self.mlp(x)

class ArticleModel(tf.keras.Model):
    def __init__(self, article_lookup_layer, article_embedding_layer):
        super().__init__()
        self.article_lookup = article_lookup_layer
        self.article_embedding = article_embedding_layer

        self.product_type_lookup = tf.keras.layers.StringLookup(
            vocabulary=unique_product_type, mask_token=None
        )
        self.product_type_embedding = tf.keras.layers.Embedding(
            self.product_type_lookup.vocabulary_size(), PRODUCT_TYPE_EMBEDDING_DIM
        )

        self.section_lookup = tf.keras.layers.StringLookup(
            vocabulary=unique_section, mask_token=None
        )
        self.section_embedding = tf.keras.layers.Embedding(
            self.section_lookup.vocabulary_size(), SECTION_EMBEDDING_DIM
        )

        self.product_group_lookup = tf.keras.layers.StringLookup(
            vocabulary=unique_product_group, mask_token=None
        )
        self.product_group_embedding = tf.keras.layers.Embedding(
            self.product_group_lookup.vocabulary_size(), PRODUCT_GROUP_EMBEDDING_DIM
        )

        self.desc_encoder = tf.keras.Sequential(
            [
                desc_vectorizer,
                tf.keras.layers.Embedding(desc_vectorizer.vocabulary_size(), DESC_EMBEDDING_DIM),
                tf.keras.layers.GlobalAveragePooling1D(),
            ]
        )
        self.mlp = tf.keras.Sequential([
            tf.keras.layers.Dense(MLP_LAYER_1, activation="relu"),
            tf.keras.layers.Dropout(MLP_DROPOUT),
            tf.keras.layers.Dense(MLP_LAYER_2),
        ])

    def call(self, features):
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
        return self.mlp(x)

# Build candidate dataset for evaluation.
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
        user_embeddings = self.customer_model(features)
        item_embeddings = self.article_model(features)
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
            monitor=monitor_metric, patience=8, mode="max",
            restore_best_weights=True, verbose=1),

        tf.keras.callbacks.ReduceLROnPlateau(
            monitor=monitor_metric, mode="max", factor=0.1, patience=3,
            min_lr=1e-4, cooldown=1, verbose=1),

        tf.keras.callbacks.TensorBoard(log_dir=log_dir),

        tf.keras.callbacks.ModelCheckpoint(
            filepath=ckpt_path, monitor=monitor_metric, mode="max",
            save_weights_only=True, save_best_only=True, verbose=1),

        tf.keras.callbacks.CSVLogger(csv_path),

        tf.keras.callbacks.TerminateOnNaN(),
    ]

    model = TwoTowerModel(CustomerModel(article_lookup, article_embedding),
                        ArticleModel(article_lookup, article_embedding))
    model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=LEARNING_RATE))

    # Log model architecture summary for layer sizes/params.
    model.customer_model.build({
        "customer_id": (None,),
        "age_scaled": (None,),
        "club_member_status": (None,),
        "fashion_news_frequency": (None,),
        "favorite_sales_channel": (None,),
        "history_article_ids": (None, MAX_HISTORY),
    })

    model.article_model.build({
        "article_id": (None,),
        "product_type_name": (None,),
        "section_name": (None,),
        "product_group_name": (None,),
        "detail_desc": (None,),
    })

    model.build({
        "customer_id": (None,),
        "age_scaled": (None,),
        "club_member_status": (None,),
        "fashion_news_frequency": (None,),
        "favorite_sales_channel": (None,),
        "history_article_ids": (None, MAX_HISTORY),
        "article_id": (None,),
        "product_type_name": (None,),
        "section_name": (None,),
        "product_group_name": (None,),
        "detail_desc": (None,),
    })
    
    summary_buf = io.StringIO()
    model.summary(print_fn=lambda x: summary_buf.write(x + "\n"))
    mlflow.log_text(summary_buf.getvalue(), "model_summary.txt")

    mlflow.log_params({
        "max_history": MAX_HISTORY,
        "batch_size": BATCH_SIZE,
        "train_split": TRAIN_SPLIT,
        "random_seed": RANDOM_SEED,
        "epochs": EPOCHS,
        "monitor_metric": monitor_metric,
        "optimizer": "Adagrad",
        "learning_rate": LEARNING_RATE,
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
    best_val = max(history.history.get(monitor_metric, [-float("inf")]))
    mlflow.log_metric(f"best_{monitor_metric}", best_val)

print("Training Over! Now exiting process.")
print(DASHLINE)
