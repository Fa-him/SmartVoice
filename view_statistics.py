from Backend.PerformanceLogger import logger

if __name__ == "__main__":
    print("\n🔍 Generating Performance Statistics...\n")
    logger.print_statistics()
    logger.export_for_paper()
    
    # Also show comparison if available
    try:
        print("\n" + "="*60)
        logger.print_comparison_stats()
        logger.export_comparison_for_paper()
    except:
        print("\n(No comparison data yet - run in COMPARISON_MODE to generate)\n")
    
    print("\nDone!\n")