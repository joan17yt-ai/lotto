"""
Algorithmic Prediction and Combination Generation Engine for Baloto, Revancha, and MiLoto.
Implements 4 distinct mathematical and behavioral strategies with combinatorial filtering.
"""

import random
from typing import List, Dict, Any, Optional

try:
    from .analyzer import LotteryAnalyzer
    from .database import save_prediction
except (ImportError, ValueError):
    from analyzer import LotteryAnalyzer
    from database import save_prediction

class LotteryPredictor:
    def __init__(self, game: str):
        self.game = game.lower()
        self.analyzer = LotteryAnalyzer(self.game)
        self.max_number = self.analyzer.max_number
        self.has_superball = self.analyzer.has_superball
        self.max_superball = self.analyzer.max_superball

    def _select_superball(self, mode: str = "balanced") -> Optional[int]:
        if not self.has_superball:
            return None
        freq = self.analyzer.get_frequency_stats()["superball_stats"]
        if not freq:
            return random.randint(1, 16)

        if mode == "hot":
            top_sb = [x["number"] for x in freq[:4]]
            return random.choice(top_sb)
        elif mode == "cold":
            least_sb = [x["number"] for x in freq[-4:]]
            return random.choice(least_sb)
        else:
            # Weighted random choice based on count_total
            numbers = [x["number"] for x in freq]
            weights = [x["count_total"] + 1 for x in freq]
            return random.choices(numbers, weights=weights, k=1)[0]

    def _is_valid_combination(self, combo: List[int], dist_metrics: Dict[str, Any]) -> bool:
        """Verifies combinatorial quality filters."""
        if len(combo) != 5 or len(set(combo)) != 5:
            return False

        sorted_c = sorted(combo)
        s = sum(sorted_c)
        opt_range = dist_metrics["sum_metrics"]["optimal_range"]

        # 1. Sum Filter: Must fall within the interquartile range (IQR)
        if not (opt_range[0] <= s <= opt_range[1]):
            return False

        # 2. Parity Filter: 3P-2I or 2P-3I (over 65% of all draws)
        evens = sum(1 for x in sorted_c if x % 2 == 0)
        if evens not in [2, 3]:
            return False

        # 3. Consecutiveness Filter: Maximum 1 pair of adjacent numbers (e.g. 14, 15)
        consec_count = 0
        for i in range(len(sorted_c) - 1):
            if sorted_c[i + 1] - sorted_c[i] == 1:
                consec_count += 1
        if consec_count > 1:
            return False

        # 4. Range Coverage Filter: Must not have all 5 numbers in a single tier
        low = sum(1 for x in sorted_c if x <= 14)
        mid = sum(1 for x in sorted_c if 15 <= x <= 28)
        high = sum(1 for x in sorted_c if x >= 29)
        if low >= 4 or mid >= 4 or high >= 4:
            return False

        return True

    def generate_balanced(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Strategy 1: Gaussian & Parity Balanced
        Generates combinations adhering strictly to historical Gaussian sum bell-curves,
        optimal parity balance (2P/3I or 3P/2I), and multi-tier range spread.
        """
        dist_metrics = self.analyzer.get_distribution_metrics()
        freq_stats = self.analyzer.get_frequency_stats()["number_stats"]
        
        # Build probability distribution based on moderate historical frequency
        weights = {x["number"]: max(1, x["count_total"]) for x in freq_stats}
        all_nums = list(range(1, self.max_number + 1))
        weight_list = [weights[n] for n in all_nums]

        results = []
        attempts = 0
        while len(results) < count and attempts < 2000:
            attempts += 1
            # Sample 5 numbers using weighted sampling without replacement
            sampled = []
            pool_nums = list(all_nums)
            pool_weights = list(weight_list)
            for _ in range(5):
                choice = random.choices(pool_nums, weights=pool_weights, k=1)[0]
                idx = pool_nums.index(choice)
                pool_nums.pop(idx)
                pool_weights.pop(idx)
                sampled.append(choice)

            if self._is_valid_combination(sampled, dist_metrics):
                sb = self._select_superball("balanced")
                combo = sorted(sampled)
                rationale = f"Suma {sum(combo)} en rango óptimo [{dist_metrics['sum_metrics']['optimal_range'][0]}-{dist_metrics['sum_metrics']['optimal_range'][1]}], balance par/impar equilibrado y dispersión controlada."
                results.append({
                    "strategy": "Equilibrada (Gauss + Paridad)",
                    "numbers": combo,
                    "superball": sb,
                    "sum": sum(combo),
                    "rationale": rationale
                })

        return results

    def generate_hot_trend(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Strategy 2: Momentum & Co-occurrence (Hot Numbers)
        Combines top performing numbers in recent draws with verified co-occurrence pairs.
        """
        freq_stats = self.analyzer.get_frequency_stats(recent_window=30)
        hot_nums = [x["number"] for x in freq_stats["number_stats"] if x["category"] == "HOT"]
        if len(hot_nums) < 5:
            hot_nums = [x["number"] for x in freq_stats["number_stats"][:12]]

        pairs_info = self.analyzer.get_top_pairs_and_triplets(top_n=10)
        dist_metrics = self.analyzer.get_distribution_metrics()

        results = []
        attempts = 0
        while len(results) < count and attempts < 2000:
            attempts += 1
            # Pick a top pair
            top_pair = random.choice(pairs_info["top_pairs"])["pair"]
            # Complete with hot numbers
            remaining_pool = [n for n in hot_nums if n not in top_pair]
            if len(remaining_pool) < 3:
                remaining_pool = [n for n in range(1, self.max_number + 1) if n not in top_pair]

            chosen = top_pair + random.sample(remaining_pool, 3)
            if self._is_valid_combination(chosen, dist_metrics):
                sb = self._select_superball("hot")
                combo = sorted(chosen)
                rationale = f"Incluye pareja frecuente {top_pair} y balotas en racha reciente con Superbalota caliente."
                results.append({
                    "strategy": "Tendencia Caliente (Momentum)",
                    "numbers": combo,
                    "superball": sb,
                    "sum": sum(combo),
                    "rationale": rationale
                })

        return results

    def generate_cold_rebound(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Strategy 3: Mean Reversion / Overdue Gap (Rezagados)
        Focuses on numbers with the highest overdue streak, stabilized with 2 high-frequency anchors.
        """
        delays = self.analyzer.get_gap_and_delay_stats()
        overdue_pool = [x["number"] for x in delays if x["status"] == "RETRASADO"]
        if len(overdue_pool) < 3:
            overdue_pool = [x["number"] for x in delays[:10]]

        freq_stats = self.analyzer.get_frequency_stats()["number_stats"]
        anchor_pool = [x["number"] for x in freq_stats[:10] if x["number"] not in overdue_pool]

        dist_metrics = self.analyzer.get_distribution_metrics()

        results = []
        attempts = 0
        while len(results) < count and attempts < 2000:
            attempts += 1
            # Pick 3 overdue numbers and 2 anchors
            pick_overdue = random.sample(overdue_pool, min(3, len(overdue_pool)))
            pick_anchors = random.sample(anchor_pool, 5 - len(pick_overdue))
            chosen = pick_overdue + pick_anchors

            if self._is_valid_combination(chosen, dist_metrics):
                sb = self._select_superball("cold")
                combo = sorted(chosen)
                rationale = f"Reversión a la media con rezagados {pick_overdue} y anclas de alta frecuencia {pick_anchors}."
                results.append({
                    "strategy": "Reversión a la Media (Rezagados)",
                    "numbers": combo,
                    "superball": sb,
                    "sum": sum(combo),
                    "rationale": rationale
                })

        return results

    def generate_anti_crowd(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Strategy 4: Game Theory / Anti-Crowd (Descorrelación de apuestas populares)
        Most people bet calendar dates (1-31). This selects numbers to minimize shared prizes.
        """
        dist_metrics = self.analyzer.get_distribution_metrics()
        high_pool = [n for n in range(32, self.max_number + 1)]
        low_pool = [n for n in range(1, 32)]

        results = []
        attempts = 0
        while len(results) < count and attempts < 2000:
            attempts += 1
            # Pick at least 2 or 3 high numbers (> 31)
            num_high = min(len(high_pool), random.choice([2, 3]))
            chosen_high = random.sample(high_pool, num_high)
            chosen_low = random.sample(low_pool, 5 - num_high)
            chosen = chosen_high + chosen_low

            if self._is_valid_combination(chosen, dist_metrics):
                sb = self._select_superball("balanced")
                combo = sorted(chosen)
                rationale = f"Optimización de premio individual: incluye balotas altas {chosen_high} fuera del rango de cumpleaños (1-31) para no compartir pozo."
                results.append({
                    "strategy": "Anti-Aglomeración (Teoría de Juegos)",
                    "numbers": combo,
                    "superball": sb,
                    "sum": sum(combo),
                    "rationale": rationale
                })

        return results

    def generate_full_ticket_pack(self) -> List[Dict[str, Any]]:
        """Generates a complete multi-strategy portfolio."""
        pack = []
        pack.extend(self.generate_balanced(1))
        pack.extend(self.generate_hot_trend(1))
        pack.extend(self.generate_cold_rebound(1))
        pack.extend(self.generate_anti_crowd(1))
        return pack
