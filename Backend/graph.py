"""
LangGraph Execution Graph - Production Ready
"""

from datetime import date
import sys
import os

# Check dependencies
try:
    from langgraph.graph import StateGraph, END
    from dotenv import load_dotenv
    import pandas as pd
except ImportError:
    print("❌ Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)

load_dotenv()

from Backend.state import AgentState
from nodes import (
    researcher_node,
    pulse_coder_node,
    clustering_node,
    synthesis_node,
    qa_node,
    formatter_node
)


def create_retail_trends_graph():
    """Creates the production workflow graph."""
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("pulse_coder", pulse_coder_node)
    workflow.add_node("clustering", clustering_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("qa", qa_node)
    workflow.add_node("formatter", formatter_node)
    
    # Sequential flow
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "pulse_coder")
    workflow.add_edge("pulse_coder", "clustering")
    workflow.add_edge("clustering", "synthesis")
    workflow.add_edge("synthesis", "qa")
    workflow.add_edge("qa", "formatter")
    workflow.add_edge("formatter", END)
    
    return workflow.compile()


def export_results(state: AgentState, output_dir: str = "./output"):
    """Export Excel workbook, markdown, and QA report."""
    
    from datetime import datetime
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    country = state['country'].replace(" ", "_")
    
    # Excel
    excel_path = os.path.join(output_dir, f"{country}_Appendix_{timestamp}.xlsx")
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        for sheet_name, df in state['excel_dataframes'].items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"✅ Excel saved: {excel_path}")
    
    # Markdown
    markdown_path = os.path.join(output_dir, f"{country}_Report_{timestamp}.md")
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(state['front_section_markdown'])
    print(f"✅ Markdown saved: {markdown_path}")
    
    # QA Report
    qa_path = os.path.join(output_dir, f"{country}_QA_{timestamp}.txt")
    with open(qa_path, 'w', encoding='utf-8') as f:
        f.write("QA VALIDATION REPORT\n" + "="*60 + "\n\n")
        for check in state['qa_checks']:
            f.write(f"Check {check.check_number}: {check.check_description}\n")
            f.write(f"Status: {check.status}\n")
            if check.notes:
                f.write(f"Notes: {check.notes}\n")
            f.write("\n")
        f.write(f"\nOverall: {'PASSED' if state['qa_passed'] else 'FAILED'}\n")
    print(f"✅ QA report saved: {qa_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    
    # Run configuration
    run_config = {
        "country": "United Kingdom",
        "timeline_start": date(2024, 1, 1),
        "timeline_end": date(2024, 6, 30),
        "retailers_in_scope": ["Tesco", "Sainsbury's", "Asda", "Morrisons", "Marks & Spencer"],
        
        "raw_articles": [],
        "retailer_structure_maps": [],
        "pulses": [],
        "whisper_tags": [],
        "macro_trends": [],
        "cipher_regroupings": [],
        "attribute_regroupings": [],
        "tech_trends": [],
        "unassigned_whispertags": [],
        "falsification_records": [],
        "qa_checks": [],
        "qa_passed": False,
        "excel_dataframes": {},
        "front_section_markdown": "",
        "errors": [],
        "warnings": []
    }
    
    print(f"\n📋 Configuration:")
    print(f"   Country: {run_config['country']}")
    print(f"   Timeline: {run_config['timeline_start']} to {run_config['timeline_end']}")
    print(f"   Retailers: {', '.join(run_config['retailers_in_scope'])}")
    print(f"\n{'='*70}\n")
    
    # Build and run graph
    print("🔧 Building workflow graph...")
    graph = create_retail_trends_graph()
    
    print("🚀 Starting execution...\n")
    
    try:
        final_state = graph.invoke(run_config)
        
        print(f"\n{'='*70}")
        print("✅ WORKFLOW COMPLETED")
        print(f"{'='*70}\n")
        
        print(f"📊 Results:")
        print(f"   Pulses: {len(final_state['pulses'])}")
        print(f"   Whisper Tags: {len(final_state['whisper_tags'])}")
        print(f"   Macro Trends: {len(final_state['macro_trends'])}")
        print(f"   Tech Trends: {len(final_state['tech_trends'])}")
        print(f"   QA: {'✅ PASSED' if final_state['qa_passed'] else '❌ FAILED'}")
        

        if final_state.get('warnings'):
            print(f"\n⚠️ Warnings ({len(final_state['warnings'])}):")
            for w in final_state['warnings'][:5]:
                print(f"   - {w}")
        
        print(f"\n📁 Exporting results...")
        export_results(final_state)
        
        print(f"\n{'='*70}")
        print("🎉 COMPLETE!")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()