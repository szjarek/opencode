#!/usr/bin/env python3

import argparse
import json
import os
import re
from datetime import datetime, timezone
from typing import List, Dict, Any

def parse_llm_logs(log_file_path: str, start_datetime: datetime) -> List[Dict[str, Any]]:
    """
    Parse LLM logs from a file and extract LLM requests, LLM responses, tool requests, and tool responses.
    
    Args:
        log_file_path: Path to the log file
        start_datetime: Datetime to start parsing from
    
    Returns:
        List of LLM request/response and tool request/response objects
    """
    llm_entries = []
    
    try:
        with open(log_file_path, 'r') as file:
            for line in file:
                # Skip empty lines
                if not line.strip():
                    continue
                    
                # Parse timestamp from log line
                # Log format: INFO 2025-11-15T14:07:30 +0ms service=config ...
                parts = line.strip().split()
                if len(parts) < 3:
                    continue
                    
                try:
                    # Parse the timestamp part (second element in split)
                    timestamp_str = parts[1]
                    
                    # Ensure timestamp is in expected format
                    if not timestamp_str:
                        continue
                    
                    # Parse full timestamp including milliseconds
                    # Example: 2025-01-23T12:00:00.123Z
                    if 'Z' in timestamp_str:
                        # Handle milliseconds and timezone
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        # Parse without milliseconds 
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                    
                    # Make timestamp timezone-aware to match start_datetime
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    
                    # If timestamp is before start datetime, skip
                    if timestamp < start_datetime:
                        continue
                except (ValueError, IndexError):
                    continue
                
                if '"type":"LLM request"' in line:
                    line_type = "LLM request" 
                elif '"type":"LLM response"' in line:
                    line_type = "LLM response" 
                elif '"type":"tool request"' in line:
                    line_type = "tool request"
                elif '"type":"tool response"' in line:
                    line_type = "tool response"
                else:
                    line_type = "unknown"
                
                if line_type in ["LLM request", "LLM response", "tool request", "tool response"]:
                    json_match = re.search(r'\{.*\}', line)
                    if json_match:
                        group_str = json_match.group(0)
                        try:
                            entry = json.loads(group_str)
                            llm_entries.append(entry)
                        except json.JSONDecodeError:
                            llm_entries.append({"type": line_type, "unparsed_content": group_str})

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
        # Make start_datetime timezone-aware for proper comparison
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
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