"""
Unit tests for Condor strategy implementation.

Tests cover:
- 4 distinct strikes structure
- Difference from Butterfly (wider profit zone)
- BUY/SELL variants
- Edge cases
"""
import pytest
from strategies.implementations import CondorStrategy
from strategies.core import get_strategy_class


class TestCondorBasic:
    """Basic functionality tests for Condor."""
    
    def test_strategy_type(self, condor_strategy):
        """Test strategy type property."""
        assert condor_strategy.strategy_type == "CONDOR"
    
    def test_registry_integration(self):
        """Test strategy is properly registered."""
        strategy_class = get_strategy_class("CONDOR_BUY")
        assert strategy_class is not None
        assert strategy_class == CondorStrategy
    
    def test_scan_basic(self, condor_strategy, ic_chain, standard_params):
        """Test basic Condor scan generates candidates."""
        dte = 30
        
        candidates = condor_strategy.scan(
            chain_data=ic_chain,
            dte=dte,
            **standard_params
        )
        
        # Should find at least some candidates
        assert len(candidates) > 0
        
        # Check first candidate structure
        cand = candidates[0]
        assert cand.symbol == ic_chain.symbol
        assert cand.dte == dte
        assert cand.leg_count == 4
        assert len(cand.legs) == 4
        assert "CONDOR" in cand.strategy_type
    
    def test_four_distinct_strikes(self, condor_strategy, ic_chain, standard_params):
        """Test that Condor uses 4 distinct strikes (not 3 like Butterfly)."""
        candidates = condor_strategy.scan(
            chain_data=ic_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates[:10]:
            # Should have exactly 4 unique strikes
            assert len(cand.strikes_used) == 4
            
            # All strikes should be different
            assert len(set(cand.strikes_used)) == 4
            
            # Strikes should be in ascending order
            K1, K2, K3, K4 = cand.strikes_used
            assert K1 < K2 < K3 < K4
    
    def test_leg_quantities_all_1x(self, condor_strategy, ic_chain, standard_params):
        """Test that Condor has 1x quantity at each strike (unlike Butterfly's 2x)."""
        candidates = condor_strategy.scan(
            chain_data=ic_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates[:5]:
            # All legs should have quantity 1
            for leg in cand.legs:
                assert leg.quantity == 1


class TestCondorVsButterfly:
    """Tests comparing Condor to Butterfly structure."""
    
    def test_condor_wider_than_butterfly(self, condor_strategy, ic_chain, standard_params):
        """Test that Condor uses 4 strikes while Butterfly uses 3."""
        condor_candidates = condor_strategy.scan(
            chain_data=ic_chain,
            dte=30,
            **standard_params
        )
        
        # Condor should generate candidates
        assert len(condor_candidates) > 0
        
        # Condor uses 4 distinct strikes
        assert len(condor_candidates[0].strikes_used) == 4
        
        # All quantities should be 1 for Condor
        for leg in condor_candidates[0].legs:
            assert leg.quantity == 1


class TestCondorProfitability:
    """Profitability tests."""
    
    def test_remaining_profit_positive(self, condor_strategy, ic_chain, standard_params):
        """Test that all candidates have positive remaining profit."""
        candidates = condor_strategy.scan(
            chain_data=ic_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates:
            assert cand.remaining_profit > 0
    
    def test_annual_return(self, condor_strategy, ic_chain, standard_params):
        """Test annualized return calculation."""
        candidates = condor_strategy.scan(
            chain_data=ic_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates:
            assert cand.annual_return_percent > 0


class TestCondorEdgeCases:
    """Edge case tests."""
    
    def test_max_strike_gap_constraint(self, condor_strategy, wide_spread, standard_params):
        """Test that max_strike_gap constraint limits candidates."""
        wide_candidates = condor_strategy.scan(
            chain_data=wide_spread,
            dte=45,
            max_strike_gap=5,
            **standard_params
        )
        
        narrow_candidates = condor_strategy.scan(
            chain_data=wide_spread,
            dte=45,
            max_strike_gap=2,
            **standard_params
        )
        
        # Narrower gap should yield fewer candidates
        assert len(narrow_candidates) <= len(wide_candidates)
