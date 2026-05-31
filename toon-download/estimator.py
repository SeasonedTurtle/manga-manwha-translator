from quota_tracker import get_remaining_quota

def estimate_pipeline_run(num_chapters, avg_pages=60, pages_per_strip=5):
    print("\n==================================================")
    print(f"  PIPELINE ESTIMATION DIAGNOSTIC: {num_chapters} CHAPTERS")
    print("==================================================")
    
    # Pull dynamic quota from our local ledger
    remaining_quota = get_remaining_quota()
    
    # API Math
    strips_per_chapter = avg_pages / pages_per_strip
    total_api_calls = int(strips_per_chapter * num_chapters)
    
    print(f"\n[QUOTA CHECK]")
    print(f" -> Current Available Quota: {remaining_quota} / 500")
    print(f" -> Estimated API Calls Required: {total_api_calls} pings")
    
    if total_api_calls > remaining_quota:
        print(f" -> [!] WARNING: This batch requires {total_api_calls} requests.")
        print(f" -> [!] You only have {remaining_quota} left today.")
        print(" -> [!] The script WILL crash. Reduce the number of chapters.")
        return False
    else:
        print(f" -> Status: SAFE. You will have {remaining_quota - total_api_calls} daily requests remaining after this run.")

    # Time Estimation Variables (in seconds)
    avg_scrape_stitch_time = 25  
    api_response_time = 7        
    api_sleep_delay = 5          
    typeset_time_per_strip = 2   
    chapter_cooldown = 60        
    
    # Time Math
    time_per_chapter = avg_scrape_stitch_time + (strips_per_chapter * (api_response_time + api_sleep_delay + typeset_time_per_strip))
    total_processing_time = time_per_chapter * num_chapters
    total_cooldown_time = chapter_cooldown * (num_chapters - 1) if num_chapters > 1 else 0
    grand_total_seconds = total_processing_time + total_cooldown_time
    
    # Format into Hours, Minutes, Seconds
    hours = int(grand_total_seconds // 3600)
    minutes = int((grand_total_seconds % 3600) // 60)
    seconds = int(grand_total_seconds % 60)
    
    print(f"\n[TIME ESTIMATION]")
    print(f" -> ESTIMATED TOTAL RUNTIME: {hours}h {minutes}m {seconds}s")
    print("==================================================\n")
    
    return True