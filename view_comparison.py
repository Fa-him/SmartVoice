from Backend.PerformanceLogger import logger

if __name__ == "__main__":
    print("\n🔬 Generating Comparison Statistics...\n")
    logger.print_comparison_stats()
    logger.export_comparison_for_paper()
    print("\nDone! Check 'Data/comparison_for_paper.txt'\n")