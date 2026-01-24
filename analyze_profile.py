import pstats
import glob
import os

def analyze_latest_profile():
    # Find most recent stats file
    files = glob.glob('lottery_profile_*.stats')
    if not files:
        print("No profile files found")
        return
        
    latest_file = max(files, key=os.path.getctime)
    print(f"\nAnalyzing profile: {latest_file}\n")
    
    # Load stats
    stats = pstats.Stats(latest_file)
    
    # Print different views of the data
    print("🕒 Top 20 time-consuming calls (cumulative):")
    stats.strip_dirs().sort_stats('cumulative').print_stats(20)
    
    print("\n📊 Top 20 calls by internal time:")
    stats.strip_dirs().sort_stats('time').print_stats(20)
    
    print("\n🔄 Callers of get_address_balance:")
    stats.strip_dirs().print_callers('get_address_balance')

if __name__ == '__main__':
    analyze_latest_profile()
