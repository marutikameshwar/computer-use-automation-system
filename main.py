import argparse
import logging
from src.orchestrator.orchestrator import Orchestrator
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://localhost:5000"
DEFAULT_GOAL = (
    "Search for member 12345, navigate to their dashboard, "
    "initiate a savings transaction of 500, reach the confirmation page, "
    "extract the full text of the paragraph that starts with 'Successfully processed' "
    "into a variable named 'transaction_receipt', and then immediately output an action "
    "of wait with a value of DONE."
)

def main():
    parser = argparse.ArgumentParser(description="Computer-Use Automation Orchestrator")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="The starting URL")
    parser.add_argument("--goal", type=str, default=DEFAULT_GOAL, help="The natural language goal for discovery")
    
    args = parser.parse_args()
    
    orchestrator = Orchestrator(capability_name="mock_bank_tx")
    artifact_path = orchestrator.resolve_version()
    
    if artifact_path is None:
        setup_logger("discovery")
        logger.info("==================================================")
        logger.info("      COMPUTER-USE AUTOMATION ORCHESTRATOR      ")
        logger.info("==================================================")
        orchestrator.run_discovery(goal=args.goal, start_url=args.url)
        artifact_path = orchestrator.resolve_version()

    if artifact_path is None:
        logger.error("Discovery failed to produce a blueprint. Exiting.")
        return

    setup_logger("replay")
    while True:
        print("\n")
        print("==================================================")
        member_id = input("Enter Member ID (e.g. 12345, 999, 500, 888, 'q' to quit): ").strip()
        
        if member_id.lower() in ['q', 'quit', 'exit']:
            print("Exiting orchestrator...")
            break
            
        if not member_id:
            member_id = "12345"
            
        logger.info("==================================================")
        logger.info(f"      STARTING REPLAY FOR MEMBER: {member_id}     ")
        logger.info("==================================================")
        
        # Always resolve latest artifact in case a previous run escalated and generated a new version
        current_artifact_path = orchestrator.resolve_version()
        
        try:
            orchestrator.run_replay(member_id=member_id, start_url=args.url, artifact_path=current_artifact_path)
        except Exception as e:
            logger.error(f"Execution failed for {member_id}: {e}")

if __name__ == "__main__":
    main()
