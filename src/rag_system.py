"""
RAG System - Retrieval Augmented Generation
Similar SRFs খুঁজে context তৈরি করে SQL generation এর জন্য
"""
import logging
from typing import List, Dict
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG implementation - simple এবং effective"""
    
    def __init__(self, embedding_manager, confidence_threshold=0.7):
        self.embedding_manager = embedding_manager
        self.confidence_threshold = confidence_threshold
        
    def retrieve_context(self, query_srf: str, max_results: int = 5) -> Dict:
        """
        Query SRF এর জন্য relevant context retrieve করি
        """
        try:
            # Similar SRFs search করি
            similar_items = self.embedding_manager.search_similar_srfs(
                query_srf, n_results=max_results
            )
            
            # High confidence items filter করি
            high_confidence_items = [
                item for item in similar_items 
                if item['similarity_score'] >= self.confidence_threshold
            ]
            
            # Context তৈরি করি
            context = {
                'query_srf': query_srf,
                'total_similar_found': len(similar_items),
                'high_confidence_count': len(high_confidence_items),
                'similar_examples': high_confidence_items,
                'all_similar': similar_items,
                'confidence_threshold': self.confidence_threshold
            }
            
            logger.info(f"Retrieved context: {len(high_confidence_items)} high-confidence matches")
            return context
            
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return {
                'query_srf': query_srf,
                'error': str(e),
                'similar_examples': [],
                'all_similar': []
            }
    
    def format_context_for_llm(self, context: Dict) -> str:
        """
        LLM এর জন্য context format করি
        """
        query_srf = context.get('query_srf', '')
        similar_examples = context.get('similar_examples', [])
        
        # Context prompt তৈরি করি
        formatted_context = ""
        
        # Similar examples add করি
        #for i, example in enumerate(similar_examples, 1):
        if(len(similar_examples) >  0):
            example = similar_examples[0]  # Assuming we only use the first example for simplicity
            similarity_score = example.get('similarity_score', 0)
            srf_text = example.get('srf_text', '').replace('SRF: ', '')
            sql_query = example.get('sql_query', '')
                
            formatted_context += f"""
           
            ---Old SRF:  
            {srf_text}

            ---Old SQL Query with detail comments with step by step instruction: 
            {sql_query}

            ---New SRF (for which SQL query needs to be generated): 
            {query_srf}

            """
        
        
        return formatted_context
    
    # def format_context_for_llm(self, context: Dict) -> str:
    #         """
    #         LLM এর জন্য context format করি এবং নির্দেশ ও কোড আলাদা করি।
    #         """
    #         query_srf = context.get('query_srf', '')
    #         similar_examples = context.get('similar_examples', [])
            
    #         formatted_context = ""
            
    #         if similar_examples:
    #             example = similar_examples[0]
    #             srf_text = example.get('srf_text', '')
    #             sql_query_full = example.get('sql_query', '')

    #             # STEP 0 (নির্দেশ) এবং বাকি SQL কোড আলাদা করা
    #             instructions = ""
    #             sql_code = ""
    #             if "----- STEP 0:" in sql_query_full:
    #                 parts = sql_query_full.split("----- STEP 1:")
    #                 instructions = parts[0]
    #                 if len(parts) > 1:
    #                     sql_code = "----- STEP 1:" + parts[1] # STEP 1 থেকে শুরু
    #             else:
    #                 sql_code = sql_query_full

    #             # XML ট্যাগ দিয়ে সুন্দরভাবে সাজানো
    #             formatted_context = f"""
    # <REFERENCE_SRF>
    # {srf_text}
    # </REFERENCE_SRF>

    # <REFERENCE_INSTRUCTIONS>
    # {instructions}
    # </REFERENCE_INSTRUCTIONS>

    # <REFERENCE_SQL_CODE>
    # {sql_code}
    # </REFERENCE_SQL_CODE>

    # <NEW_SRF>
    # {query_srf}
    # </NEW_SRF>
    # """


    def analyze_retrieval_quality(self, context: Dict) -> Dict:
        """
        Retrieval quality analyze করি
        """
        similar_examples = context.get('similar_examples', [])
        all_similar = context.get('all_similar', [])
        
        if not all_similar:
            return {
                'quality': 'poor',
                'reason': 'No similar examples found',
                'recommendation': 'Add more training data'
            }
        
        avg_similarity = sum(item['similarity_score'] for item in all_similar) / len(all_similar)
        high_confidence_ratio = len(similar_examples) / len(all_similar)
        
        # Quality determination
        if avg_similarity >= 0.8 and high_confidence_ratio >= 0.6:
            quality = 'excellent'
        elif avg_similarity >= 0.7 and high_confidence_ratio >= 0.4:
            quality = 'good'
        elif avg_similarity >= 0.6:
            quality = 'fair'
        else:
            quality = 'poor'
        
        analysis = {
            'quality': quality,
            'avg_similarity': avg_similarity,
            'high_confidence_ratio': high_confidence_ratio,
            'total_examples': len(all_similar),
            'high_confidence_examples': len(similar_examples)
        }
        
        # Recommendations
        if quality == 'poor':
            analysis['recommendation'] = 'Consider adding more similar training examples'
        elif quality == 'fair':
            analysis['recommendation'] = 'Results may need manual review'
        else:
            analysis['recommendation'] = 'Good quality retrieval, proceed with confidence'
        
        return analysis

# Usage functions
def test_rag_retrieval(embedding_manager, test_srf):
    """
    RAG system test করার জন্য
    """
    print("🔍 Testing RAG retrieval system...")
    
    # RAG system তৈরি করি
    rag = RAGSystem(embedding_manager)
    
    # Context retrieve করি
    context = rag.retrieve_context(test_srf)
    
    # Results show করি
    print(f"\n📊 Retrieval Results:")
    print(f"  Total similar found: {context.get('total_similar_found', 0)}")
    print(f"  High confidence matches: {context.get('high_confidence_count', 0)}")
    
    # Quality analysis
    quality_analysis = rag.analyze_retrieval_quality(context)
    print(f"\n🎯 Quality Analysis:")
    print(f"  Quality: {quality_analysis['quality']}")
    print(f"  Average similarity: {quality_analysis['avg_similarity']:.3f}")
    print(f"  Recommendation: {quality_analysis['recommendation']}")
    
    # Formatted context for LLM
    formatted_context = rag.format_context_for_llm(context)
    print(f"\n📝 Formatted context length: {len(formatted_context)} characters")
    
    # Save context for inspection
    with open("./data/test_context.txt", "w", encoding="utf-8") as f:
        f.write(formatted_context)
    print("💾 Context saved to ./data/test_context.txt")
    
    return rag, context

# Direct run করার জন্য
if __name__ == "__main__":
    # Test করার জন্য embedding manager থাকতে হবে
    print("⚠️  First run embedding_manager.py to setup embeddings")
    print("Then you can test RAG system")
    
    # Example usage:
    # from embedding_manager import EmbeddingManager
    # manager = EmbeddingManager()
    # test_srf = "Commission calculation for MyBL campaign"
    # rag, context = test_rag_retrieval(manager, test_srf)
