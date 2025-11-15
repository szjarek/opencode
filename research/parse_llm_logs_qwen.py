#!/usr/bin/env python3

import argparse
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any

def parse_llm_logs(log_file_path: str, start_datetime: datetime) -> List[Dict[str, Any]]:
    """
    Parse LLM logs from a file and extract only LLM requests and responses.
    
    Args:
        log_file_path: Path to the log file
        start_datetime: Datetime to start parsing from
    
    Returns:
        List of LLM request/response objects
    """
    llm_entries = []
    
    try:
        with open(log_file_path, 'r') as file:
            for line in file:
                # Skip empty lines
                if not line.strip():
                    continue
                    
                # Parse timestamp from log line
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)', line)
                if not timestamp_match:
                    continue
                    
                timestamp_str = timestamp_match.group(1)
                try:
                    # Parse timestamp to datetime object
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    # If timestamp is before start datetime, skip
                    if timestamp < start_datetime:
                        continue
                except ValueError:
                    continue
                
                # Look for LLM request or response entries
                if '"LLM request"' in line or '"LLM response"' in line:
                    # Find JSON part in the line
                    json_match = re.search(r'\{.*\}', line)
                    if json_match:
                        try:
                            entry = json.loads(json_match.group(0))
                            llm_entries.append(entry)
                        except json.JSONDecodeError:
                            continue
    
    except FileNotFoundError:
        print(f"Error: Log file '{log_file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error reading log file: {e}")
        return []
    
    return llm_entries

def main():
    # Default values
    default_log_file = os.path.expanduser("~/.local/share/opencode/log/dev.log")
    default_start_datetime = datetime.min
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Parse LLM logs and extract LLM requests/responses')
    parser.add_argument('--log-file', default=default_log_file, 
                       help=f'Path to log file (default: {default_log_file})')
    parser.add_argument('--start-datetime', default='1970-01-01T00:00:00.000Z',
                       help='Start datetime in ISO format (default: beginning of log file)')
    
    args = parser.parse_args()
    
    # Parse start datetime
    try:
        start_datetime = datetime.fromisoformat(args.start_datetime.replace('Z', '+00:00'))
    except ValueError:
        print(f"Error: Invalid datetime format. Expected ISO format (e.g. '2023-01-01T12:00:00.000Z')")
        return
    
    # Parse LLM logs
    print(f"Parsing logs from {args.log_file} starting from {start_datetime}.")
    llm_entries = parse_llm_logs(args.log_file, start_datetime)
    
    # Write to output file
    output_file = "log.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(llm_entries, f, indent=2)
        print(f"Extracted {len(llm_entries)} LLM requests/responses to {output_file}")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")

if __name__ == "__main__":
    main()