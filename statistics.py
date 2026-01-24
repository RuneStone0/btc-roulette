"""
Statistics and probability calculations for Bitcoin address brute-forcing.

This module demonstrates the computational infeasibility of brute-forcing
Bitcoin addresses by calculating probabilities and time estimates.
"""

import time
from typing import Dict, Optional
from datetime import timedelta


class BruteForceStatistics:
    """Track statistics and calculate probabilities for brute-forcing attempts."""
    
    # BIP39 constants
    BIP39_ENTROPY_BITS = 128  # 12-word seed phrase
    BIP39_TOTAL_COMBINATIONS = 2 ** BIP39_ENTROPY_BITS  # 2^128
    
    # Bitcoin address space (simplified - actual is larger due to multiple address types)
    BITCOIN_ADDRESS_SPACE = 2 ** 160  # Simplified estimate
    
    def __init__(self):
        self.start_time = time.time()
        self.total_attempts = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.last_update_time = self.start_time
        self.attempts_per_second = 0.0
        
    def record_attempt(self, success: bool = False):
        """Record a balance check attempt.
        
        Args:
            success: Whether the address had funds (True) or not (False)
        """
        self.total_attempts += 1
        if success:
            self.successful_checks += 1
        else:
            self.failed_checks += 1
        
        # Update rate every 10 attempts
        if self.total_attempts % 10 == 0:
            self._update_rate()
    
    def _update_rate(self):
        """Update the attempts per second rate."""
        current_time = time.time()
        elapsed = current_time - self.last_update_time
        if elapsed > 0:
            # Calculate rate based on last 10 attempts
            recent_attempts = 10
            self.attempts_per_second = recent_attempts / elapsed
        self.last_update_time = current_time
    
    def _safe_timedelta(self, seconds: float) -> Optional[timedelta]:
        """Safely create timedelta, handling overflow for very large numbers.
        
        Args:
            seconds: Number of seconds (can be very large)
            
        Returns:
            timedelta object or None if too large
        """
        # timedelta can handle up to about 2^63 seconds
        MAX_TIMEDELTA_SECONDS = 2**63 - 1
        try:
            if seconds > MAX_TIMEDELTA_SECONDS:
                return None
            return timedelta(seconds=int(seconds))
        except (OverflowError, ValueError):
            return None
    
    def _format_large_time(self, seconds: float) -> str:
        """Format very large time values in human-readable format.
        
        Args:
            seconds: Number of seconds
            
        Returns:
            Formatted string
        """
        if seconds <= 0:
            return "0 seconds"
        
        # Try timedelta first for reasonable values
        delta = self._safe_timedelta(seconds)
        if delta:
            return str(delta)
        
        # For very large values, use scientific notation with context
        years = seconds / (365.25 * 24 * 3600)
        if years >= 1e12:
            return f"{years:.2e} years (longer than the age of the universe)"
        elif years >= 1e9:
            return f"{years/1e9:.2f} billion years"
        elif years >= 1e6:
            return f"{years/1e6:.2f} million years"
        elif years >= 1e3:
            return f"{years/1e3:.2f} thousand years"
        else:
            return f"{years:.2f} years"
    
    def get_statistics(self) -> Dict:
        """Get current statistics.
        
        Returns:
            Dict with statistics including attempts, rate, probabilities, and time estimates
        """
        elapsed_time = time.time() - self.start_time
        
        # Calculate probabilities
        prob_single_attempt = 1.0 / self.BIP39_TOTAL_COMBINATIONS
        prob_so_far = self.total_attempts / self.BIP39_TOTAL_COMBINATIONS
        
        # Estimate time to check 1% of space
        time_for_one_percent_seconds = None
        time_for_one_percent_formatted = None
        if self.attempts_per_second > 0:
            one_percent = self.BIP39_TOTAL_COMBINATIONS / 100
            time_for_one_percent_seconds = one_percent / self.attempts_per_second
            time_for_one_percent_formatted = self._format_large_time(time_for_one_percent_seconds)
        
        # Estimate time to check all space (theoretical)
        time_for_all_seconds = None
        time_for_all_formatted = None
        if self.attempts_per_second > 0:
            time_for_all_seconds = self.BIP39_TOTAL_COMBINATIONS / self.attempts_per_second
            time_for_all_formatted = self._format_large_time(time_for_all_seconds)
        
        return {
            'total_attempts': self.total_attempts,
            'successful_checks': self.successful_checks,
            'failed_checks': self.failed_checks,
            'elapsed_time': elapsed_time,
            'elapsed_time_formatted': str(timedelta(seconds=int(elapsed_time))),
            'attempts_per_second': self.attempts_per_second,
            'probability_single_attempt': prob_single_attempt,
            'probability_so_far': prob_so_far,
            'probability_so_far_percent': prob_so_far * 100,
            'estimated_time_for_1_percent_seconds': time_for_one_percent_seconds,
            'estimated_time_for_1_percent': time_for_one_percent_formatted,
            'estimated_time_for_all_seconds': time_for_all_seconds,
            'estimated_time_for_all': time_for_all_formatted,
            'bip39_total_combinations': self.BIP39_TOTAL_COMBINATIONS,
            'bip39_total_combinations_scientific': f"{self.BIP39_TOTAL_COMBINATIONS:.2e}"
        }
    
    def format_statistics(self) -> str:
        """Format statistics as a human-readable string.
        
        Returns:
            Formatted string with statistics
        """
        stats = self.get_statistics()
        
        # Make it more fun and visual
        lines = [
            "📊 Your Progress So Far:",
            f"  🎯 Total Attempts: {stats['total_attempts']:,}",
            f"  ✅ Successful Checks: {stats['successful_checks']}",
            f"  ❌ Failed Checks: {stats['failed_checks']:,}",
            f"  ⏱️  Elapsed Time: {stats['elapsed_time_formatted']}",
            f"  🚀 Speed: {stats['attempts_per_second']:.2f} attempts/second",
            "",
            "🎲 The Math Behind It:",
            f"  • Probability per attempt: {stats['probability_single_attempt']:.2e}",
            f"  • Space checked so far: {stats['probability_so_far_percent']:.2e}%",
            f"  • Total address space: {stats['bip39_total_combinations_scientific']} combinations",
            ""
        ]
        
        # Add time estimates if available
        if stats.get('estimated_time_for_1_percent'):
            lines.append(f"  ⏱️  Time to check 1%: {stats['estimated_time_for_1_percent']}")
        
        if stats.get('estimated_time_for_all'):
            lines.append(f"  ⏱️  Time to check all: {stats['estimated_time_for_all']}")
        
        # Add fun comparison
        if stats['probability_so_far_percent'] < 1e-30:
            lines.append("")
            lines.append("💭 Fun Fact: You've checked less than 0.0000000000000000000000000001% of the space!")
            lines.append("   That's like finding a specific grain of sand on all the beaches on Earth! 🏖️")
        
        lines.append("")
        lines.append("🔐 This is why Bitcoin cryptography is so secure!")
        
        return "\n".join(lines)
    
    def get_educational_message(self) -> str:
        """Get an educational message about the infeasibility.
        
        Returns:
            Educational message string
        """
        stats = self.get_statistics()
        
        # Make it more fun and engaging
        combinations = stats['bip39_total_combinations_scientific']
        
        # Fun comparisons
        fun_facts = [
            "🌌 There are more possible seed phrases than atoms in the observable universe!",
            "🎲 You're more likely to win the lottery every day for a year than find a funded address",
            "⚡ Even if you checked 1 million addresses per second, it would take longer than the age of the universe",
            "🔐 This is why Bitcoin is secure - the math is on your side (if you keep your keys safe!)"
        ]
        
        # Build message
        message = [
            "\n🎰 Welcome to the Bitcoin Roulette! 🎰\n",
            "=" * 70,
            "📚 Educational Fun Facts:",
            f"  • BIP39 seed phrases have 2^128 ({combinations}) possible combinations",
            ""
        ]
        
        # Add rate-specific info if we have attempts
        if stats['attempts_per_second'] > 0:
            time_estimate = stats.get('estimated_time_for_1_percent', 'an extremely long time')
            message.append(f"  • At {stats['attempts_per_second']:.2f} attempts/second, checking 1% would take: {time_estimate}")
        else:
            message.append("  • Starting up... Your speed will be calculated after a few attempts!")
            message.append("  • Typical speeds: Electrum (5-20/sec) or Blockstream API (1-2/sec)")
        
        message.append("")
        message.extend(fun_facts)
        message.append("")
        message.append("💡 Remember: This is for educational purposes only!")
        message.append("=" * 70)
        
        return "\n".join(message)


def calculate_probability_info() -> Dict:
    """Calculate and return probability information for educational purposes.
    
    Returns:
        Dict with probability calculations
    """
    stats = BruteForceStatistics()
    
    # Example rates
    rates = {
        'electrum_fast': 20,  # queries per second
        'electrum_slow': 5,
        'blockstream': 1.5,
        'theoretical_max': 1000000  # 1 million per second (unrealistic)
    }
    
    one_percent = stats.BIP39_TOTAL_COMBINATIONS / 100
    
    results = {}
    for name, rate in rates.items():
        time_1pct_seconds = one_percent / rate
        time_all_seconds = stats.BIP39_TOTAL_COMBINATIONS / rate
        
        # Create temporary stats instance to use formatting methods
        temp_stats = BruteForceStatistics()
        results[name] = {
            'rate': rate,
            'time_for_1_percent_seconds': time_1pct_seconds,
            'time_for_1_percent': temp_stats._format_large_time(time_1pct_seconds),
            'time_for_all_seconds': time_all_seconds,
            'time_for_all': temp_stats._format_large_time(time_all_seconds)
        }
    
    return {
        'bip39_combinations': stats.BIP39_TOTAL_COMBINATIONS,
        'bip39_combinations_scientific': f"{stats.BIP39_TOTAL_COMBINATIONS:.2e}",
        'one_percent': one_percent,
        'scenarios': results
    }
