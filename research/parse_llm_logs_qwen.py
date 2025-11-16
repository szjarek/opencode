#!/usr/bin/env python3

import argparse
import json
import os
import re
from datetime import datetime, timezone
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
                    
                    # Parse just the date and time part (ignoring milliseconds offset for now)
                    # Add timezone info to make it timezone-aware to match start_datetime 
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
                    # Make timestamp timezone-aware to match start_datetime
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                    
                    # If timestamp is before start datetime, skip
                    if timestamp < start_datetime:
                        continue
                except (ValueError, IndexError):
                    continue
                
                 # Look for LLM request or response entries
                if 'LLM request' in line or 'LLM response' in line:
                    line = line.strip()
                    line_type = 'LLM_request' if line.endswith('LLM request') else 'LLM_response'

                    # Find JSON part in the line                    
                    json_match = re.search(r'\{.*\}', line)
                    if json_match:
                        group_str = json_match.group(0)
                        try:
                            # Handle double-escaped JSON strings by first decoding the escaped string
                            # This handles cases where JSON contains escaped quotes, newlines, etc.
                            try:
                                decoded_group_str = group_str.encode().decode('unicode_escape')
                                entry = json.loads(decoded_group_str)
                                llm_entries.append({line_type: entry})
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                # If decoding fails, try direct parsing as fallback
                                entry = json.loads(group_str)
                                llm_entries.append({line_type: entry})
                        except json.JSONDecodeError:
                            llm_entries.append({line_type: group_str})

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