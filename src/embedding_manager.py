"""
Embedding Manager - ChromaDB এবং Semantic Embeddings manage করার জন্য
Enhanced with batch processing, metadata filtering, and performance optimization
"""
import chromadb
from sentence_transformers import SentenceTransformer
import json
import logging
import statistics
import time
from pathlib import Path
import uuid
from functools import lru_cache
from config.settings import settings
import concurrent.futures

from data_processor import DataProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Enhanced Embeddings create ও manage করার জন্য class"""
    
    def __init__(self, chroma_db_path=None, embedding_model="all-MiniLM-L6-v2", 
                 hnsw_config=None):
        if chroma_db_path is None:
            # Use absolute path by default
            script_dir = Path(__file__).parent.parent.absolute()
            chroma_db_path = script_dir / "data" / "embeddings"
        
        self.chroma_db_path = Path(chroma_db_path)
        self.embedding_model_name = embedding_model
          # Configure HNSW parameters
        if hnsw_config is None:
            hnsw_config = {
                "M": settings.HNSW_M,
                "construction_ef": settings.HNSW_EF_CONSTRUCTION,
                "search_ef": settings.HNSW_EF_SEARCH
            }
        self.hnsw_config = hnsw_config
        
        # ChromaDB setup with new client configuration
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_db_path)
        )
          # Sentence transformer model load
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info("✅ Embedding model loaded successfully!")
        
        # Collection তৈরি করি
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """ChromaDB collection তৈরি বা load করি with HNSW configuration"""
        try:
            collection = self.chroma_client.get_or_create_collection(
                name="srf_sql_embeddings",                metadata={
                    "description": "SRF-SQL pairs embeddings for Commission AI",
                    "hnsw:M": self.hnsw_config["M"],
                    "hnsw:construction_ef": self.hnsw_config["construction_ef"],
                    "hnsw:search_ef": self.hnsw_config["search_ef"]
                },
                embedding_function=None  # We provide our own embeddings
            )
            logger.info("✅ ChromaDB collection ready with HNSW indexing!")
            return collection
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise

    def create_embeddings_from_data(self, processed_data, batch_size=None, force_recreate=False):
        """
        Process data in batches for better memory management with metadata
        force_recreate=True: নতুন ট্রেনিং ডাটার জন্য পুরো collection replace করবে
        force_recreate=False: আগে থেকে embedding থাকলে skip করবে
        """
        if batch_size is None:
            batch_size = settings.RAG_BATCH_SIZE
            
        # Smart check: আগে থেকে embedding আছে কিনা
        if not force_recreate and self.has_existing_embeddings():
            existing_count = self.collection.count()
            logger.info(f"✅ Found {existing_count} existing embeddings, skipping recreation")
            logger.info("� Use force_recreate=True for new training data")
            return True
            
        try:
            total_items = len(processed_data)
            logger.info(f"Creating embeddings for {total_items} items in batches of {batch_size}")
            
            # Clear existing data (নতুন ডাটার জন্য বা force recreate এর জন্য)
            self._clear_existing_data()
            
            # Process in batches
            for i in range(0, total_items, batch_size):
                batch = processed_data[i:i+batch_size]
                
                documents_batch = []
                metadatas_batch = []
                ids_batch = []
                
                for idx, item in enumerate(batch):
                    doc_id = f"doc_{i+idx}"
                    srf_text = item['srf_text']
                    
                    # Skip empty SRF
                    if not srf_text.strip():
                        continue
                    
                    # মেটাডাটা তৈরি করি
                    metadata = {
                        "commission_type": item.get('commission_type', 'unknown'),
                        "commission_name": item.get('commission_name', 'unknown'),
                        "srf_length": item['srf_length'],
                        "sql_length": item['sql_length'],
                        "has_supporting_table": item.get('has_supporting_table', False),
                        "sub_category": item.get('sub_category', 'other'),
                        "sql_query": item.get('sql_query', ''),
                    }
                    
                    documents_batch.append(srf_text)
                    metadatas_batch.append(metadata)
                    ids_batch.append(doc_id)
                
                if not documents_batch:
                    continue
                
                # Generate embeddings for batch
                logger.info(f"Generating embeddings for batch {i//batch_size + 1}/{(total_items+batch_size-1)//batch_size}")
                embeddings_batch = self.embedding_model.encode(documents_batch, show_progress_bar=True)
                
                # Store batch in ChromaDB
                self.collection.add(
                    documents=documents_batch,
                    embeddings=embeddings_batch.tolist(),
                    metadatas=metadatas_batch,
                    ids=ids_batch
                )
                
                logger.info(f"✅ Batch {i//batch_size + 1} completed: {len(documents_batch)} embeddings")
            
            logger.info("✅ Successfully created all embeddings!")
            return True
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            return False
    
    def _clear_existing_data(self):
        """Clear existing embeddings for fresh start"""
        try:
            # Get all existing IDs first
            existing_data = self.collection.get()
            if existing_data['ids']:
                self.collection.delete(ids=existing_data['ids'])
                logger.info(f"Cleared {len(existing_data['ids'])} existing embeddings")
            else:
                logger.info("No existing embeddings to clear")
        except Exception as e:
            logger.warning(f"Could not clear existing data: {str(e)}")
            # If clearing fails, recreate collection
            try:
                self.chroma_client.delete_collection("srf_sql_embeddings")
                self.collection = self._get_or_create_collection()
                logger.info("Recreated collection after clear failure")
            except:
                logger.warning("Could not recreate collection, continuing with existing")

    def search_similar_srfs(self, query_srf, n_results=5, filter_metadata=None):
        """
        Enhanced search with metadata filtering and performance optimization
        """
        try:

            # Query embedding তৈরি করি
            query_embedding = self.embedding_model.encode([query_srf])

            processor = DataProcessor()
            meta_data = processor.extract_commission_metadata(query_srf)
            
            filter_metadata = filter_metadata or {}
            filter_metadata['commission_type'] = meta_data.get('commission_type', 'unknown')
            # Build where clause for filtering
            where_clause = None
            if filter_metadata:
                where_clause = {}
                for key, value in filter_metadata.items():
                    where_clause[key] = {"$eq": value}
            
            # Search করি with optional filtering
            search_kwargs = {
                "query_embeddings": query_embedding.tolist(),
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if where_clause:
                search_kwargs["where"] = where_clause
            
            results = self.collection.query(**search_kwargs)
            
            # Results format করি
            similar_items = []
            
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    similarity_score = 1 - results['distances'][0][i]  # Convert distance to similarity
                    
                    # Extract clean SRF text (remove "SRF: " prefix if exists)
                    srf_text = results['documents'][0][i]
                    if srf_text.startswith("SRF: "):
                        srf_text = srf_text[5:]
                    
                    item = {
                        'similarity_score': similarity_score,
                        'srf_text': srf_text,
                        'metadata': results['metadatas'][0][i]
                    }
                    
                    # Add SQL query if it exists in metadata
                    if 'sql_query' in results['metadatas'][0][i]:
                        item['sql_query'] = results['metadatas'][0][i]['sql_query']
                    
                    similar_items.append(item)
            
            logger.info(f"Found {len(similar_items)} similar SRFs")
            return similar_items
            
        except Exception as e:
            logger.error(f"Error searching similar SRFs: {str(e)}")
            return []
    
    @lru_cache(maxsize=settings.RAG_CACHE_SIZE)
    def _cached_search(self, query_hash, n_results, filter_str):
        """Cached version of search for performance"""
        # This is a placeholder - in real implementation, 
        # we'd need to implement proper caching
        pass
    
    def get_collection_info(self):
        """Collection এর information দেখি"""
        try:
            count = self.collection.count()
            return {
                'total_embeddings': count,
                'collection_name': 'srf_sql_embeddings',
                'embedding_model': self.embedding_model_name
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {}

    def has_existing_embeddings(self):
        """Check করি collection এ embedding আছে কিনা"""
        try:
            count = self.collection.count()
            return count > 0
        except Exception as e:
            logger.warning(f"Could not check existing embeddings: {str(e)}")
            return False
    
    def force_recreate_embeddings(self, processed_data, batch_size=None):
        """Force করে নতুন embedding তৈরি করি (নতুন ট্রেনিং ডাটার জন্য)"""
        logger.info("🔄 Force recreating embeddings for new training data...")
        return self.create_embeddings_from_data(processed_data, batch_size, force_recreate=True)

# Usage example function
def setup_embeddings_from_processed_data(processed_data_file, force_recreate=False):
    """
    Processed data থেকে embeddings setup করার main function
    force_recreate=True: নতুন ট্রেনিং ডাটার জন্য পুরো collection replace
    force_recreate=False: আগে থেকে embedding থাকলে skip
    """
    print("🚀 Starting embedding setup...")
    
    # Processed data load করি
    try:
        with open(processed_data_file, 'r', encoding='utf-8') as f:
            processed_data = json.load(f)
        print(f"📄 Loaded {len(processed_data)} processed items")
    except Exception as e:
        print(f"❌ Error loading processed data: {str(e)}")
        return False
    
    # Embedding manager তৈরি করি
    try:
        embedding_manager = EmbeddingManager()
        print("✅ Embedding manager initialized")
    except Exception as e:
        print(f"❌ Error initializing embedding manager: {str(e)}")
        return False
      # Embeddings তৈরি করি (smart logic দিয়ে)
    success = embedding_manager.create_embeddings_from_data(processed_data, force_recreate=force_recreate)
    
    if success:
        # Collection info দেখি
        info = embedding_manager.get_collection_info()
        print("\n📊 Embedding Collection Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        print("\n🎉 Embedding setup completed successfully!")
        return embedding_manager
    else:
        print("\n😔 Embedding setup failed!")
        return None

# Test function
def test_similarity_search(embedding_manager, test_srf):
    """
    Similarity search test করার জন্য
    """
    print(f"\n🔍 Testing similarity search with SRF: {test_srf[:100]}...")
    
    similar_items = embedding_manager.search_similar_srfs(test_srf, n_results=3)
    
    print(f"\n📋 Found {len(similar_items)} similar items:")
    for i, item in enumerate(similar_items, 1):
        print(f"\n  {i}. Similarity Score: {item['similarity_score']:.3f}")
        print(f"     SRF: {item['srf_text'][:150]}...")
        print(f"     SQL: {item['sql_query'][:100]}...")

# Direct run করার জন্য
if __name__ == "__main__":
    # Processed data file path
    processed_file = "./data/training_data/processed_training_data.json"
    
    # Embeddings setup করি
    manager = setup_embeddings_from_processed_data(processed_file)
    
    if manager:
        # Test করি
        test_srf = "Commission calculation for MyBL campaign with hourly commission structure"
        test_similarity_search(manager, test_srf)
