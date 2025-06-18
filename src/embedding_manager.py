"""
Embedding Manager - ChromaDB এবং Semantic Embeddings manage করার জন্য
Simple এবং beginner-friendly
"""
import chromadb
from sentence_transformers import SentenceTransformer
import json
import logging
from pathlib import Path
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Embeddings create ও manage করার জন্য simple class"""
    
    def __init__(self, chroma_db_path=None, embedding_model="all-MiniLM-L6-v2"):
        if chroma_db_path is None:
            # Use absolute path by default
            script_dir = Path(__file__).parent.parent.absolute()
            chroma_db_path = script_dir / "data" / "embeddings"
        
        self.chroma_db_path = Path(chroma_db_path)
        self.embedding_model_name = embedding_model
        
        # ChromaDB setup
        self.chroma_client = chromadb.PersistentClient(path=str(self.chroma_db_path))
        
        # Sentence transformer model load
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info("✅ Embedding model loaded successfully!")
        
        # Collection তৈরি করি
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """ChromaDB collection তৈরি বা load করি"""
        try:
            collection = self.chroma_client.get_or_create_collection(
                name="srf_sql_embeddings",
                metadata={"description": "SRF-SQL pairs embeddings for Commission AI"}
            )
            logger.info("✅ ChromaDB collection ready!")
            return collection
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise
    
    def create_embeddings_from_data(self, processed_data):
        """
        Processed data থেকে embeddings তৈরি করি
        """
        try:
            logger.info(f"Creating embeddings for {len(processed_data)} items...")
              # Existing data clear করি (fresh start এর জন্য)
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
            
            documents = []
            metadatas = []
            ids = []
            
            for item in processed_data:
                # SRF text কে document হিসেবে use করি
                srf_text = item['srf_text']
                
                # Skip empty SRF
                if not srf_text.strip():
                    continue
                
                # Document তৈরি করি (SRF + supporting table info)
                document = f"SRF: {srf_text}"
                if item.get('supporting_table'):
                    document += f"\nSupporting Table: {item['supporting_table'][:500]}"  # First 500 chars
                
                documents.append(document)
                
                # Metadata তৈরি করি
                metadata = {
                    'item_id': str(item['id']),
                    'sql_query': item['sql_query'],
                    'srf_length': item['srf_length'],
                    'sql_length': item['sql_length']
                }
                metadatas.append(metadata)
                
                # Unique ID তৈরি করি
                ids.append(f"srf_{item['id']}_{uuid.uuid4().hex[:8]}")
            
            # Batch এ embeddings তৈরি করি
            logger.info("Generating embeddings...")
            embeddings = self.embedding_model.encode(documents, show_progress_bar=True)
            
            # ChromaDB তে store করি
            logger.info("Storing in ChromaDB...")
            self.collection.add(
                documents=documents,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ Successfully created and stored {len(documents)} embeddings!")
            return True
            
        except Exception as e:
            logger.error(f"Error creating embeddings: {str(e)}")
            return False
    
    def search_similar_srfs(self, query_srf, n_results=5):
        """
        নতুন SRF এর জন্য similar SRFs খুঁজি
        """
        try:
            # Query embedding তৈরি করি
            query_document = f"SRF: {query_srf}"
            query_embedding = self.embedding_model.encode([query_document])
            
            # Search করি
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results
            )
            
            # Results format করি
            similar_items = []
            
            if results['documents']:
                for i in range(len(results['documents'][0])):
                    item = {
                        'similarity_score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'srf_text': results['documents'][0][i],
                        'sql_query': results['metadatas'][0][i]['sql_query'],
                        'item_id': results['metadatas'][0][i]['item_id']
                    }
                    similar_items.append(item)
            
            logger.info(f"Found {len(similar_items)} similar SRFs")
            return similar_items
            
        except Exception as e:
            logger.error(f"Error searching similar SRFs: {str(e)}")
            return []
    
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

# Usage example function
def setup_embeddings_from_processed_data(processed_data_file):
    """
    Processed data থেকে embeddings setup করার main function
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
    
    # Embeddings তৈরি করি
    success = embedding_manager.create_embeddings_from_data(processed_data)
    
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
