from app.agents import AgentDataInitializer
from app.config import config

if __name__ == "__main__":
    # Initialize data
    initializer = AgentDataInitializer()
    
    # Use actual JSON file path
    rightmove_file = f"{config.root_path}/dataset/rent_cast_data/processed/rightmove_data_processed.json"

    # Initialize all data
    initializer.initialize_all_data(rightmove_file, tenant_count=200)
