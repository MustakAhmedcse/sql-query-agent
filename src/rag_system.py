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
    
    def format_context_for_llm(self, context: Dict,target=None) -> str:
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

            <REFERENCE_SRF>
            {srf_text}
            </REFERENCE_SRF>

            <REFERENCE_SQL_CODE>
            {sql_query}
            {Report_Setup_Query}
            </REFERENCE_SQL_CODE>

            <NEW_SRF> -- (for which SQL query needs to be generated)
            {query_srf}
            </NEW_SRF>
            
            {f"<TARGET>{target}</TARGET>" if target else ""}
        
            """
        
        
        return formatted_context


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

Reference_Instructions = """
SPECIAL INSTRUCTION BLOCK FOR LLM INTEGRATION:
                1. REMOVE ALL COMMENT LINES WHEN NEW QUERY IS GENERATED FOR A NEW SRF,
                EXCEPT THE FOLLOWING TYPES WHICH MUST BE RETAINED:
                a. Comments containing DROP, CREATE, SELECT statements
                b. Comments showing row counts (e.g., -- 71730 Rows)
                c. Comments referencing IDs (e.g., -- REPORT_ID : 0011)
                2. BASE_CYCLE: Extract the month from the commission END DATE (e.g., 31-Mar-2025 ? 'Mar_25'), then get the CYCLEID from COMMISSIONCYCLE.
                3. PUBLISH_CYCLE: Extract the current month (e.g., if today is 30-Jun-2025 ? 'Jun_25'), then get the CYCLEID from COMMISSIONCYCLE.
                4. Use BASE_CYCLE and PUBLISH_CYCLE values in the FINALIZE_REPORT_ADHOC procedure.
                5. KEEP THE SQL FORMAT AND SEQUENCE INTACT. DO NOT MODIFY STRUCTURE UNLESS EXPLICITLY INSTRUCTEDS.
"""

Report_Setup_Query = """"
    --------------------------------- REPORT SETUP QUERY -----------------------------------------

    --STEP 5: PREPARE FOR REPORT PUBLISHING
    --REPORT_ID : 0011
    SELECT REPORTID REPORT_ID FROM COMMISSIONREPORT WHERE REPORTNAME = 'Commission for MyBL Hourly_16th Mar25 to 31st Mar25';
    --BASE_CYCLE_ID : 0022 
    --SPECIAL INSTRUCTION : BASE_CYCLE = month of commission END DATE (Mar-25)
    SELECT CYCLEID BASE_CYCLE_ID  FROM COMMISSIONCYCLE WHERE CYCLEDESCRIPTION = 'Mar_25'; -- commission end date (BASE_CYCLE/REPORT_MONTH): 31-Mar-2025 → 'Mar_25'
    --REPORT_CYCLE_ID : 0033
    SELECT REPORT_CYCLE_ID,* FROM COMMISSIONCYCLEREPORTS where REPORTID = 0011 and  CYCLEID = 0022; 

    --CHECK ADHOC TABLE DATA
    SELECT * FROM ad_hoc_data where REPORT_CYCLE_ID = 0033;
    --delete from ad_hoc_data where REPORT_CYCLE_ID = 0033;
    --commit;

    --INSERT THE CHANNEL WISE CALCULATED COMMISSION DATA
    INSERT INTO AD_HOC_DATA (ID, REPORT_CYCLE_ID, CHANNEL_CODE,COMMISSION_AMOUNT,AMOUNT_TYPE_ID,AMOUNT)
    SELECT AD_HOC_DATA_ID.NEXTVAL ID, 0033 REPORT_CYCLE_ID, DD_CODE, COMMISSION_AMOUNT,1,TOTAL_RECHARGE
    FROM (
    SELECT DD_CODE, SUM(RECHARGE_AMOUNT*HIT) TOTAL_RECHARGE, SUM(COMMISSION_AMOUNT)  COMMISSION_AMOUNT
    FROM TEMP_FOR_DET1_MYBL_16_31MAR25
    GROUP BY DD_CODE
    );
    commit;

    --CHECK SUM OF COMMISSION AMOUNT
    SELECT SUM(COMMISSION_AMOUNT) FROM ad_hoc_data where REPORT_CYCLE_ID = 0033; --  476868.5  

    --PUBLISH_CYCLE_ID : 0044 
    --SPECIAL INSTRUCTION : PUBLISH_CYCLE = current sysdate month (e.g. Jun-25 if today = 30-Jun-2025)
    SELECT CYCLEID PUBLISH_CYCLE_ID FROM COMMISSIONCYCLE WHERE CYCLEDESCRIPTION = 'Apr_25'; --PUBLISH_CYCLE(REPORT_PUBLISH_MONTH)

    --STEP 6: SET UP COMMISSION DETAILS IN COMMISSION PLATFORM
    --PROC_COMMISSION_DETAIL_SETUP(<REPORT_TITLE>, <PUBLISH_CYCLE_ID>, <DETAIL1>, <LEVEL1>, ..., <DETAIL9>, <LEVEL9>);
    EXEC PROC_COMMISSION_DETAIL_SETUP('Commission for MyBL Hourly_16th Mar25 to 31st Mar25',0044,'TEMP_FOR_DET1_MYBL_16_31MAR25','Deno Details');

    --STEP 7: FINALIZE AND PUBLISH COMMISSION REPORT
    --FINALIZE_REPORT_ADHOC(<REPORT_NAME>, <REPORT_CYCLE_ID>, <BASE_CYCLE>, <PUBLISH_CYCLE>, <APPROVAL_FLOW_ID>, <PUBLISH_TYPE>)
    EXEC FINALIZE_REPORT_ADHOC('Commission for MyBL Hourly_16th Mar25 to 31st Mar25', 0033,'Mar_25', 'Apr_25',290, 1);--FOLLOW THE BASE_CYCLE & PUBLISH_CYCLE SPECIAL INSTRUCTION HERE ALSO

    """

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
