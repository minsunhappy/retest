#!/usr/bin/env python3
"""
Simulate how often each interface/data pairing is shown when the fair
rotation schedule from config.js is repeated.

Example:
    python simulate_pair_distribution.py --participants 30
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

INTERFACE_ORDER = ['C', 'D', 'D1', 'Y', 'Y1']
FAIR_DATA_PERMUTATIONS = [
    [0, 1, 2, 3, 4],
    [1, 2, 3, 4, 0],
    [2, 3, 4, 0, 1],
    [3, 4, 0, 1, 2],
    [4, 0, 1, 2, 3],
]


def load_data_folders(path: Path, expected: int) -> List[str]:
    """Load the first `expected` data folders from data_folders.json."""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list) and len(data) >= expected:
                return data[:expected]
        except json.JSONDecodeError:
            pass
    # Fallback placeholder labels
    fallback = ['A', 'B', 'C', 'D', 'E']
    return fallback[:expected]


def simulate(participants: int, data_folders: List[str]) -> Dict[Tuple[str, str], int]:
    """Return how many times each (interface, data) pair occurs."""
    counts: Dict[Tuple[str, str], int] = defaultdict(int)
    schedule_len = len(FAIR_DATA_PERMUTATIONS)

    for person in range(participants):
        permutation = FAIR_DATA_PERMUTATIONS[person % schedule_len]
        for iface_idx, data_idx in enumerate(permutation):
            interface = INTERFACE_ORDER[iface_idx]
            data = data_folders[data_idx]
            counts[(interface, data)] += 1

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Count interface/data pair usage over multiple participants.'
    )
    parser.add_argument(
        '--participants',
        type=int,
        default=30,
        help='Number of simulated participants (default: 30)',
    )
    parser.add_argument(
        '--data-folders',
        type=Path,
        default=Path('data_folders.json'),
        help='Path to data_folders.json (default: ./data_folders.json)',
    )
    args = parser.parse_args()

    data_folders = load_data_folders(args.data_folders, len(INTERFACE_ORDER))
    counts = simulate(args.participants, data_folders)

    print(f'Participants: {args.participants}')
    print(f'Data folders: {data_folders}')
    print('-' * 60)
    for interface in INTERFACE_ORDER:
        for data in data_folders:
            pair = (interface, data)
            print(f'{interface} + {data}: {counts[pair]:2d}회')
        print('-' * 60)


if __name__ == '__main__':
    main()

