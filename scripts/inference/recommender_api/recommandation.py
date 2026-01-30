import pandas as pd
import numpy as np
import joblib
import ast
from typing import Dict, List
import anyio
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
import tensorflow as tf
import tensorflow_recommenders as tfrs

class RecommendationEngine:
    """Simple interface for getting fashion recommendations"""
    
    def __init__(self, model_path: str, articles_csv_path: str = '/data/processed/articles_df.csv',
                scaler_path: str = '/data/scalers/age_scaler_portugal.pkl', max_history: int = 50):
        """
        Initialize the recommendation engine.
        
        Args:
            model_path: Path to saved TensorFlow model
            articles_csv_path: Path to articles catalog CSV
            scaler_path: Path to age scaler pickle file
            max_history: Maximum purchase history length (must match training)
        """

        print(f"Loading model from {model_path}...")
        self.model = tf.saved_model.load(model_path)
        
        print(f"Loading articles catalog...")
        self.articles_df = pd.read_csv(articles_csv_path)
        self.articles_df['article_id'] = self.articles_df['article_id'].astype(str)
        
        print(f"Loading age scaler...")
        self.age_scaler = joblib.load(scaler_path)
        
        self.max_history = max_history
        print(f"Engine ready! {len(self.articles_df)} articles available.")
    
    def _pad_or_truncate(self, items: List[str]) -> List[str]:
        items = [str(x) for x in list(items)][:self.max_history]
        if len(items) < self.max_history:
            items = items + [""] * (self.max_history - len(items))
        return items

    
    def _ensure_list(self, x) -> List[str]:
        """Convert purchase history to list format"""
        if isinstance(x, list):
            return x
        if pd.isna(x):
            return []
        try:
            return ast.literal_eval(x)
        except (ValueError, SyntaxError):
            return []
    
    def recommend(self, customer_data: Dict, top_k: int = 5, exclude_purchased: bool = True) -> pd.DataFrame:
        """
        Get top-K recommendations for a customer.
        
        Args:
            customer_data: Dictionary with customer information:
                - customer_id: str (required)
                - age: int or float (required)
                - club_member_status: str (optional, e.g., "ACTIVE")
                - fashion_news_frequency: str (optional, e.g., "Regularly")
                - favorite_sales_channel: str (optional, e.g., "1")
                - purchased_articles: list of article IDs (optional)
            
            top_k: Number of recommendations to return
            exclude_purchased: Whether to exclude already purchased items
        
        Returns:
            DataFrame with top-K recommended articles and their details
        
        Example:
            >>> customer = {
            ...     'customer_id': 'C001',
            ...     'age': 28,
            ...     'club_member_status': 'ACTIVE',
            ...     'fashion_news_frequency': 'Regularly',
            ...     'favorite_sales_channel': '1',
            ...     'purchased_articles': ['0706016001', '0568601006']
            ... }
            >>> recs = engine.recommend(customer, top_k=5)
        """
        # Prepare customer features
        age_scaled = self.age_scaler.transform([[customer_data['age']]])[0][0]
        purchase_history = self._ensure_list(customer_data.get('purchased_articles', []))
        history_padded = self._pad_or_truncate(purchase_history)
        
        # Create input tensors
        input_tensors = {
            'customer_id': tf.constant([str(customer_data['customer_id'])], dtype=tf.string),
            'age_scaled': tf.constant([age_scaled], dtype=tf.float32),
            'club_member_status': tf.constant([str(customer_data.get('club_member_status', 'unknown'))], dtype=tf.string),
            'fashion_news_frequency': tf.constant([str(customer_data.get('fashion_news_frequency', 'unknown'))], dtype=tf.string),
            'favorite_sales_channel': tf.constant([str(customer_data.get('favorite_sales_channel', 'UNKNOWN'))], dtype=tf.string),
            'history_article_ids': tf.constant([history_padded], dtype=tf.string),
        }
        
        # Get customer embedding
        customer_embedding = self.model.customer_model(input_tensors, training=False)
        
        # Compute similarities with all articles
        all_scores = self._compute_article_scores(customer_embedding)
        
        # Get top candidates
        num_candidates = top_k * 2 if exclude_purchased else top_k
        top_indices = np.argsort(all_scores)[::-1][:num_candidates]
        recommended_article_ids = self.articles_df.iloc[top_indices]['article_id'].tolist()
        
        # Filter out purchased items if needed
        if exclude_purchased:
            purchased_set = set(purchase_history)
            recommended_article_ids = [
                aid for aid in recommended_article_ids 
                if aid not in purchased_set
            ][:top_k]
        
        # Get article details
        recommendations = self.articles_df[
            self.articles_df['article_id'].isin(recommended_article_ids)
        ].copy()
        
        # Preserve recommendation order
        recommendations['rank'] = recommendations['article_id'].map(
            {aid: i+1 for i, aid in enumerate(recommended_article_ids)}
        )
        recommendations = recommendations.sort_values('rank')
        
        return recommendations[[
            'rank', 'article_id', 'product_type_name', 
            'section_name', 'product_group_name', 'detail_desc'
        ]].reset_index(drop=True)
    
    def _compute_article_scores(self, customer_embedding: tf.Tensor) -> np.ndarray:
        """Compute similarity scores for all articles"""
        batch_size = 2048
        all_scores = []
        
        for i in range(0, len(self.articles_df), batch_size):
            batch_df = self.articles_df.iloc[i:i+batch_size]
            
            batch_inputs = {
                'article_id': tf.constant(batch_df['article_id'].values, dtype=tf.string),
                'product_type_name': tf.constant(batch_df['product_type_name'].fillna('unknown').astype(str).values, dtype=tf.string),
                'section_name': tf.constant(batch_df['section_name'].fillna('unknown').astype(str).values, dtype=tf.string),
                'product_group_name': tf.constant(batch_df['product_group_name'].fillna('unknown').astype(str).values, dtype=tf.string),
                'detail_desc': tf.constant(batch_df['detail_desc'].fillna('unknown').astype(str).values, dtype=tf.string),
            }
            
            article_embeddings = self.model.article_model(batch_inputs, training=False)
            batch_scores = tf.reduce_sum(customer_embedding * article_embeddings, axis=1)
            all_scores.append(batch_scores.numpy())
        
        return np.concatenate(all_scores)

def get_recommendations(model_path: str, customer_data: Dict,
                        articles_csv_path: str = '/data/processed/articles_df.csv',
                        scaler_path: str = '/data/scalers/age_scaler_portugal.pkl',
                        top_k: int = 5, exclude_purchased: bool = True) -> pd.DataFrame:
    
    """
    Simple function to get recommendations without creating an engine instance.
    
    Args:
        model_path: Path to saved model
        customer_data: Customer information dict
        articles_csv_path: Path to articles CSV
        scaler_path: Path to age scaler
        top_k: Number of recommendations
        exclude_purchased: Filter out purchased items
    
    Returns:
        DataFrame with recommendations
    """

    engine = RecommendationEngine(model_path, articles_csv_path, scaler_path)
    return engine.recommend(customer_data, top_k, exclude_purchased)


async def recommend_async(engine: RecommendationEngine, customer_data: Dict,
                          top_k: int = 5, exclude_purchased: bool = True) -> pd.DataFrame:
    return await anyio.to_thread.run_sync(
        engine.recommend,
        customer_data,
        top_k,
        exclude_purchased,
    )
