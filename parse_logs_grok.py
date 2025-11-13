#!/usr/bin/env python3
"""
Script to parse OpenCode logs and extract LLM request and response dictionaries.

Usage: python parse_logs.py <log_file_path> [--output-dir <dir>]

This script reads log files (assumed to be JSON lines format) and extracts
the structured data from "LLM request" and "LLM response" log entries.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional


def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single log line as JSON."""
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def extract_llm_logs(log_file_path: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Extract LLM request and response logs from a log file.

    Returns:
        Tuple of (requests, responses) lists containing the extracted data dictionaries.
    """
    requests = []
    responses = []

    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            log_entry = parse_log_line(line)
            if not log_entry:
                continue

            # Check if this is an LLM request or response log
            message = log_entry.get('message', '')
            data = log_entry.get('data', {})

            if message == 'LLM request' and data:
                # Add line number for debugging
                data['_log_line'] = line_num
                requests.append(data)
            elif message == 'LLM response' and data:
                # Add line number for debugging
                data['_log_line'] = line_num
                responses.append(data)

    return requests, responses


def save_extracted_data(requests: List[Dict[str, Any]], responses: List[Dict[str, Any]], output_dir: str = '.') -> None:
    """Save the extracted data to JSON files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save requests
    with open(output_path / 'llm_requests.json', 'w', encoding='utf-8') as f:
        json.dump(requests, f, indent=2, ensure_ascii=False)

    # Save responses
    with open(output_path / 'llm_responses.json', 'w', encoding='utf-8') as f:
        json.dump(responses, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(requests)} requests to {output_path / 'llm_requests.json'}")
    print(f"Saved {len(responses)} responses to {output_path / 'llm_responses.json'}")


def pair_conversations(requests: List[Dict[str, Any]], responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Pair requests and responses by sessionID and messageID.

    Returns a list of conversation dictionaries with request and response data.
    """
    # Create lookup for responses by (sessionID, messageID)
    response_lookup = {}
    for resp in responses:
        key = (resp.get('sessionID'), resp.get('messageID'))
        response_lookup[key] = resp

    conversations = []
    for req in requests:
        key = (req.get('sessionID'), req.get('messageID'))
        resp = response_lookup.get(key)

        conversation = {
            'sessionID': req.get('sessionID'),
            'messageID': req.get('messageID'),
            'request': req,
            'response': resp
        }
        conversations.append(conversation)

    return conversations


def main():
    parser = argparse.ArgumentParser(description='Parse OpenCode logs for LLM requests and responses')
    parser.add_argument('log_file', help='Path to the log file to parse')
    parser.add_argument('--output-dir', '-o', default='.',
                        help='Directory to save extracted data (default: current directory)')
    parser.add_argument('--pair-conversations', '-p', action='store_true',
                        help='Pair requests and responses into conversations')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print summary statistics')

    args = parser.parse_args()

    log_file_path = args.log_file
    if not Path(log_file_path).exists():
        print(f"Error: Log file '{log_file_path}' does not exist")
        sys.exit(1)

    # Extract the logs
    requests, responses = extract_llm_logs(log_file_path)

    if args.verbose:
        print(f"Found {len(requests)} LLM requests and {len(responses)} LLM responses")

    if args.pair_conversations:
        conversations = pair_conversations(requests, responses)
        output_path = Path(args.output_dir) / 'llm_conversations.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(conversations)} conversations to {output_path}")
    else:
        save_extracted_data(requests, responses, args.output_dir)


if __name__ == '__main__':
    main()