# backend/agents/crew.py

from crewai import Crew, Process
from backend.agents.agent_definitions import (
    create_ingestion_agent,
    create_analyzer_agent,
    create_forecast_agent,
    create_optimizer_agent,
    create_reporter_agent,
)
from backend.agents.task_definitions import (
    ingest_task,
    analyze_task,
    forecast_task,
    optimize_task,
    report_task
)
from backend.llm import rate_limiter
import time
import logging

logger = logging.getLogger(__name__)

def build_hvac_crew(task_callback=None) -> Crew:
    """Build a fresh crew with new agent instances"""
    return Crew(
        agents=[
            create_ingestion_agent(),
            create_analyzer_agent(),
            create_forecast_agent(),
            create_optimizer_agent(),
            create_reporter_agent(),
        ],
        tasks=[ingest_task, analyze_task, forecast_task, optimize_task, report_task],
        process=Process.sequential,
        verbose=True,
        memory=False,
        task_callback=task_callback,
        max_rpm=12,  # Global crew-level rate limit
    )


def run_crew_with_rate_limiting(crew: Crew, inputs: dict, delay_between_tasks: int = 3):
    """
    Run crew with additional delays between tasks
    
    Args:
        crew: The CrewAI crew instance
        inputs: Input parameters for the crew
        delay_between_tasks: Seconds to wait between each task (default: 3)
    
    Returns:
        Crew execution result
    """
    logger.info("🚀 Starting HVAC pipeline with rate limiting...")
    
    # Add delay before starting
    rate_limiter.wait_if_needed()
    
    try:
        result = crew.kickoff(inputs=inputs)
        logger.info("✅ Pipeline completed successfully")
        return result
        
    except Exception as e:
        error_msg = str(e).lower()
        
        if "rate" in error_msg or "429" in error_msg:
            logger.error("❌ Rate limit exceeded even with controls. Recommend:")
            logger.error("   1. Add more API keys to .env")
            logger.error("   2. Increase delay_between_tasks")
            logger.error("   3. Process fewer buildings per batch")
        
        raise


def batch_process_buildings(buildings: list, inputs_template: dict, batch_size: int = 5, delay_between_batches: int = 60):
    """
    Process multiple buildings in controlled batches
    
    Args:
        buildings: List of building IDs
        inputs_template: Template dict with parameters (will add building_id)
        batch_size: Number of buildings per batch (default: 5)
        delay_between_batches: Seconds to wait between batches (default: 60)
    
    Returns:
        List of results for each building
    """
    results = []
    total = len(buildings)
    
    for i in range(0, total, batch_size):
        batch = buildings[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📦 Processing Batch {batch_num}/{total_batches}")
        logger.info(f"Buildings: {batch}")
        logger.info(f"{'='*60}\n")
        
        for j, building_id in enumerate(batch):
            logger.info(f"\n🏢 Building {building_id} ({i+j+1}/{total})")
            
            # Build fresh crew for each building
            crew = build_hvac_crew()
            
            # Prepare inputs
            inputs = {**inputs_template, "building_id": building_id}
            
            try:
                result = run_crew_with_rate_limiting(crew, inputs)
                results.append({
                    "building_id": building_id,
                    "status": "success",
                    "result": result
                })
                
                # Delay between buildings within batch
                if j < len(batch) - 1:
                    logger.info(f"⏳ Cooling down 10 seconds before next building...")
                    time.sleep(10)
                    
            except Exception as e:
                logger.error(f"❌ Failed for building {building_id}: {e}")
                results.append({
                    "building_id": building_id,
                    "status": "error",
                    "error": str(e)
                })
        
        # Longer delay between batches
        if i + batch_size < total:
            logger.info(f"\n⏸️  Batch complete. Cooling down {delay_between_batches} seconds before next batch...\n")
            time.sleep(delay_between_batches)
    
    # Summary
    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(f"\n{'='*60}")
    logger.info(f"BATCH PROCESSING COMPLETE")
    logger.info(f"   Total: {total} buildings")
    logger.info(f"   Success: {success_count}")
    logger.info(f"   Failed: {total - success_count}")
    logger.info(f"{'='*60}\n")
    
    return results