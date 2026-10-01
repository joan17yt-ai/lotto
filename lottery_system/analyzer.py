"""
Statistical Analysis and Pattern Detection Engine for Baloto, Revancha, and MiLoto.
Computes frequencies, gaps/delays, Gaussian distributions, parity ratios, and co-occurrences.
"""

from collections import Counter, defaultdict
import numpy as np
from typing import List, Dict, Any, Tuple
try:
    from .database import get_draws
except (ImportError, ValueError):
    from database import get_draws

class LotteryAnalyzer:
    def __init__(self, game: str):
        self.game = game.lower()
        self.max_number = 43 if self.game in ['baloto', 'revancha'] else 39
        self.has_superball = self.game in ['baloto', 'revancha']
        self.max_superball = 16 if self.has_superball else None
        self.draws = get_draws(self.game)

    def reload(self):
        self.draws = get_draws(self.game)

    def total_draws_count(self) -> int:
        return len(self.draws)

    def get_frequency_stats(self, recent_window: int = 50) -> Dict[str, Any]:
        """Calculates all-time and recent frequency for each number."""
        all_numbers = []
        recent_numbers = []
        sb_all = []
        sb_recent = []

        for idx, d in enumerate(self.draws):
            nums = d["numbers"]
            all_numbers.extend(nums)
            if idx < recent_window:
                recent_numbers.extend(nums)
            
            if self.has_superball and d.get("superball") is not None:
                sb_all.append(d["superball"])
                if idx < recent_window:
                    sb_recent.append(d["superball"])

        all_counter = Counter(all_numbers)
        recent_counter = Counter(recent_numbers)
        sb_counter = Counter(sb_all) if self.has_superball else Counter()
        sb_recent_counter = Counter(sb_recent) if self.has_superball else Counter()

        total_draws = len(self.draws)
        window_draws = min(recent_window, total_draws)

        # Expected frequency per number in total draws: (total_draws * 5) / max_number
        expected_total = (total_draws * 5.0) / self.max_number if self.max_number else 1.0
        expected_recent = (window_draws * 5.0) / self.max_number if self.max_number else 1.0

        number_stats = []
        for n in range(1, self.max_number + 1):
            count_total = all_counter[n]
            count_recent = recent_counter[n]
            pct_total = (count_total / total_draws * 100) if total_draws > 0 else 0
            dev_total = count_total - expected_total

            # Categorize based on recent performance
            if count_recent > expected_recent * 1.25:
                category = "HOT"
            elif count_recent < expected_recent * 0.75:
                category = "COLD"
            else:
                category = "WARM"

            number_stats.append({
                "number": n,
                "count_total": count_total,
                "pct_total": round(pct_total, 2),
                "count_recent": count_recent,
                "expected_recent": round(expected_recent, 1),
                "deviation_total": round(dev_total, 2),
                "category": category
            })

        # Superball stats
        superball_stats = []
        if self.has_superball:
            for sb in range(1, self.max_superball + 1):
                count_sb = sb_counter[sb]
                pct_sb = (count_sb / total_draws * 100) if total_draws > 0 else 0
                superball_stats.append({
                    "number": sb,
                    "count_total": count_sb,
                    "pct_total": round(pct_sb, 2),
                    "count_recent": sb_recent_counter[sb]
                })

        return {
            "game": self.game,
            "total_draws": total_draws,
            "recent_window": window_draws,
            "number_stats": sorted(number_stats, key=lambda x: x["count_total"], reverse=True),
            "superball_stats": sorted(superball_stats, key=lambda x: x["count_total"], reverse=True) if self.has_superball else []
        }

    def get_gap_and_delay_stats(self) -> List[Dict[str, Any]]:
        """Calculates current streak of absence (gap) and max historical gap for each ball."""
        current_gaps = {n: None for n in range(1, self.max_number + 1)}
        intervals = defaultdict(list)
        last_seen_idx = {n: None for n in range(1, self.max_number + 1)}

        for idx, d in enumerate(self.draws):
            nums = set(d["numbers"])
            for n in range(1, self.max_number + 1):
                if n in nums:
                    if current_gaps[n] is None:
                        current_gaps[n] = idx
                    if last_seen_idx[n] is not None:
                        interval = idx - last_seen_idx[n]
                        intervals[n].append(interval)
                    last_seen_idx[n] = idx

        # For balls not seen yet in dataset
        total_draws = len(self.draws)
        for n in range(1, self.max_number + 1):
            if current_gaps[n] is None:
                current_gaps[n] = total_draws

        gap_results = []
        for n in range(1, self.max_number + 1):
            curr_gap = current_gaps[n]
            all_int = intervals[n]
            avg_int = np.mean(all_int) if all_int else (self.max_number / 5.0)
            max_gap = max(all_int) if all_int else curr_gap
            
            # Overdue index: ratio of current gap to average interval
            overdue_index = round(curr_gap / avg_int, 2) if avg_int > 0 else 0

            gap_results.append({
                "number": n,
                "current_gap": curr_gap,
                "avg_interval": round(float(avg_int), 1),
                "max_gap": int(max_gap),
                "overdue_index": overdue_index,
                "status": "RETRASADO" if overdue_index >= 1.5 else ("REGULAR" if overdue_index >= 0.7 else "FRECUENTE")
            })

        return sorted(gap_results, key=lambda x: x["current_gap"], reverse=True)

    def get_distribution_metrics(self) -> Dict[str, Any]:
        """Analyzes sums, parity balance, and decade distribution."""
        sums = []
        parity_counts = Counter()
        decades_counts = Counter()

        for d in self.draws:
            nums = d["numbers"]
            s = sum(nums)
            sums.append(s)

            # Even/Odd
            evens = sum(1 for x in nums if x % 2 == 0)
            odds = 5 - evens
            parity_counts[f"{evens}P-{odds}I"] += 1

            # Range grouping
            low = sum(1 for x in nums if x <= 14)
            mid = sum(1 for x in nums if 15 <= x <= 28)
            high = sum(1 for x in nums if x >= 29)
            decades_counts[f"L:{low}-M:{mid}-H:{high}"] += 1

        total_draws = len(self.draws)
        sums_arr = np.array(sums) if sums else np.array([100])

        parity_pct = {k: round(v / total_draws * 100, 2) for k, v in parity_counts.items()}

        return {
            "sum_metrics": {
                "mean": round(float(np.mean(sums_arr)), 1),
                "median": round(float(np.median(sums_arr)), 1),
                "std": round(float(np.std(sums_arr)), 1),
                "min": int(np.min(sums_arr)),
                "max": int(np.max(sums_arr)),
                "q25": int(np.percentile(sums_arr, 25)),
                "q75": int(np.percentile(sums_arr, 75)),
                "optimal_range": [int(np.percentile(sums_arr, 25)), int(np.percentile(sums_arr, 75))]
            },
            "parity_distribution": sorted(parity_pct.items(), key=lambda x: x[1], reverse=True),
            "total_draws": total_draws
        }

    def get_top_pairs_and_triplets(self, top_n: int = 10) -> Dict[str, List[Any]]:
        """Computes co-occurrence matrices for pairs and triplets."""
        pair_counter = Counter()
        triplet_counter = Counter()

        for d in self.draws:
            nums = d["numbers"]
            for i in range(len(nums)):
                for j in range(i + 1, len(nums)):
                    pair_counter[(nums[i], nums[j])] += 1
                    for k in range(j + 1, len(nums)):
                        triplet_counter[(nums[i], nums[j], nums[k])] += 1

        total_draws = len(self.draws)
        top_pairs = []
        for pair, count in pair_counter.most_common(top_n):
            top_pairs.append({
                "pair": list(pair),
                "count": count,
                "pct": round(count / total_draws * 100, 2)
            })

        top_triplets = []
        for triplet, count in triplet_counter.most_common(top_n):
            top_triplets.append({
                "triplet": list(triplet),
                "count": count,
                "pct": round(count / total_draws * 100, 2)
            })

        return {
            "top_pairs": top_pairs,
            "top_triplets": top_triplets
        }
