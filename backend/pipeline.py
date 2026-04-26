import time
import asyncio
from typing import Dict, Any
from loguru import logger

from backend.database import SessionLocal, PipelineRun
from backend.agents.crew import build_hvac_crew

# Global state to track live progress percentage per run_id
run_progress: dict[str, int] = {}

async def run_pipeline(run_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """
    Execute the HVAC multi-agent pipeline.
    """
    logger.info(f"Starting pipeline execution for run_id: {run_id}")
    start_time = time.time()
    
    # Initialize UI progress bar to 10% when starting
    run_progress[run_id] = 10

    db = SessionLocal()
    try:
        run = db.get(PipelineRun, run_id)
        if run:
            run.status = "running"
            db.commit()
        else:
            logger.warning(f"run_id {run_id} not found in DB at start")
            
        def task_callback(task_output):
            """Called roughly when each agent finishes its task."""
            if run_id in run_progress:
                run_progress[run_id] = min(run_progress[run_id] + 18, 90)
                logger.info(f"Pipeline {run_id} progress advanced to {run_progress[run_id]}%")

        crew = build_hvac_crew(task_callback=task_callback)
        
        # Run synchronous kickoff in a thread to avoid blocking the asyncio event loop
        result = await asyncio.to_thread(crew.kickoff, inputs=inputs)
        
        result_dict = {"raw_output": str(result), "tasks_output": {}}
        if hasattr(result, "tasks_output"):
            for t in result.tasks_output:
                result_dict["tasks_output"][t.description] = t.raw
                
        duration_s = time.time() - start_time
        
        if run:
            run.status = "completed"
            run.duration_s = duration_s
            db.commit()
            
        logger.info(f"Pipeline {run_id} completed successfully in {duration_s:.2f}s")
        return result_dict
        
    except Exception as e:
        duration_s = time.time() - start_time
        logger.exception(f"Pipeline execution failed for {run_id}: {e}")
        
        if db.is_active:
            run = db.get(PipelineRun, run_id)
            if run:
                run.status = "failed"
                run.error_msg = str(e)
                run.duration_s = duration_s
                db.commit()
                
        raise
    finally:
        db.close()
