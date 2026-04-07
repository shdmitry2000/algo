"""
Unit tests for Calendar Spread strategy implementation.

Tests cover:
- Same-strike calendars (standard time spreads)
- Diagonal calendars (different strikes)
- Multi-expiration chain handling
- DTE difference constraints
- Edge cases specific to time-based strategies
"""
import pytest
from strategies.implementations import CalendarSpreadStrategy
from strategies.core import get_strategy_class


class TestCalendarBasic:
    """Basic functionality tests for Calendar spreads."""
    
    def test_strategy_type(self, calendar_strategy):
        """Test strategy type property."""
        assert calendar_strategy.strategy_type == "CALENDAR"
    
    def test_registry_integration(self):
        """Test strategy is properly registered."""
        strategy_class = get_strategy_class("CALENDAR_BUY_C")
        assert strategy_class is not None
        assert strategy_class == CalendarSpreadStrategy
    
    def test_scan_basic(self, calendar_strategy, calendar_chain, standard_params):
        """Test basic Calendar scan generates candidates."""
        dte = 30
        
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=dte,
            **standard_params
        )
        
        # Should find at least some candidates
        assert len(candidates) > 0
        
        # Check first candidate structure
        cand = candidates[0]
        assert cand.symbol == calendar_chain.symbol
        assert cand.leg_count == 2  # Calendar has 2 legs
        assert len(cand.legs) == 2
        assert "CALENDAR" in cand.strategy_type or "DIAGONAL" in cand.strategy_type
    
    def test_requires_multi_expiration(self, calendar_strategy, ic_chain, standard_params):
        """Test that calendar requires multi-expiration chain."""
        # ic_chain has only one expiration
        candidates = calendar_strategy.scan(
            chain_data=ic_chain,
            dte=30,
            **standard_params
        )
        
        # Should return empty list (and log warning)
        assert len(candidates) == 0
    
    def test_leg_structure(self, calendar_strategy, calendar_chain, standard_params):
        """Test that Calendar candidates have correct leg structure."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates[:5]:
            # 2 legs
            assert len(cand.legs) == 2
            
            leg1, leg2 = cand.legs
            
            # Legs should have expiration field
            assert leg1.expiration is not None
            assert leg2.expiration is not None
            
            # Different expirations
            assert leg1.expiration != leg2.expiration
            
            # Same right (both call or both put)
            assert leg1.right == leg2.right


class TestCalendarSameStrike:
    """Tests for same-strike calendars (standard time spreads)."""
    
    def test_same_strike_calendars_exist(self, calendar_strategy, calendar_chain, standard_params):
        """Test that same-strike calendars are generated."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            include_diagonal=False,  # Only same-strike
            **standard_params
        )
        
        # Should find some same-strike calendars
        assert len(candidates) > 0
        
        # Verify strikes are the same
        for cand in candidates:
            leg1, leg2 = cand.legs
            assert leg1.strike == leg2.strike
    
    def test_call_and_put_calendars(self, calendar_strategy, calendar_chain, standard_params):
        """Test that both call and put calendars are generated."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            include_diagonal=False,
            **standard_params
        )
        
        call_calendars = [c for c in candidates if c.legs[0].right == "C"]
        put_calendars = [c for c in candidates if c.legs[0].right == "P"]
        
        # Should have both
        assert len(call_calendars) > 0
        assert len(put_calendars) > 0
    
    def test_near_vs_far_expiration(self, calendar_strategy, calendar_chain, standard_params):
        """Test that near and far expirations are correctly identified."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            include_diagonal=False,
            **standard_params
        )
        
        for cand in candidates[:5]:
            leg1, leg2 = cand.legs
            
            # One leg should be near-term, one far-term
            # (based on expiration dates)
            from datetime import datetime
            exp1 = datetime.strptime(leg1.expiration, "%Y-%m-%d")
            exp2 = datetime.strptime(leg2.expiration, "%Y-%m-%d")
            
            # Should be different
            assert exp1 != exp2


class TestCalendarDiagonal:
    """Tests for diagonal calendars (different strikes + different expirations)."""
    
    def test_diagonal_calendars_exist(self, calendar_strategy, calendar_chain, standard_params):
        """Test that diagonal calendars are generated."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            include_diagonal=True,
            **standard_params
        )
        
        # Filter for diagonal only
        diagonals = [c for c in candidates if "DIAGONAL" in c.strategy_type]
        
        # Should have some diagonals
        assert len(diagonals) > 0
    
    def test_diagonal_different_strikes(self, calendar_strategy, calendar_chain, standard_params):
        """Test that diagonal calendars use different strikes."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            include_diagonal=True,
            **standard_params
        )
        
        diagonals = [c for c in candidates if "DIAGONAL" in c.strategy_type]
        
        for cand in diagonals[:10]:
            leg1, leg2 = cand.legs
            
            # Different strikes
            assert leg1.strike != leg2.strike
            
            # Different expirations
            assert leg1.expiration != leg2.expiration
    
    def test_disable_diagonal(self, calendar_strategy, calendar_chain, standard_params):
        """Test that include_diagonal=False excludes diagonals."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            include_diagonal=False,
            **standard_params
        )
        
        # No diagonal candidates
        diagonals = [c for c in candidates if "DIAGONAL" in c.strategy_type]
        assert len(diagonals) == 0


class TestCalendarDTEConstraints:
    """DTE difference constraint tests."""
    
    def test_min_dte_difference(self, calendar_strategy, calendar_chain, standard_params):
        """Test minimum DTE difference constraint."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            min_dte_difference=25,  # Tight constraint
            max_dte_difference=90,
            **standard_params
        )
        
        # Verify that DTE difference is at least min
        for cand in candidates:
            if hasattr(cand, 'dte_range') and cand.dte_range:
                min_dte, max_dte = cand.dte_range
                dte_diff = max_dte - min_dte
                assert dte_diff >= 25
    
    def test_max_dte_difference(self, calendar_strategy, calendar_chain, standard_params):
        """Test maximum DTE difference constraint."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            min_dte_difference=20,
            max_dte_difference=45,  # Tight upper bound
            **standard_params
        )
        
        # Verify that DTE difference is at most max
        for cand in candidates:
            if hasattr(cand, 'dte_range') and cand.dte_range:
                min_dte, max_dte = cand.dte_range
                dte_diff = max_dte - min_dte
                assert dte_diff <= 45
    
    def test_tight_constraints_reduce_candidates(self, calendar_strategy, calendar_chain, standard_params):
        """Test that tighter DTE constraints reduce candidates."""
        wide_candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            min_dte_difference=15,
            max_dte_difference=120,
            **standard_params
        )
        
        tight_candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            min_dte_difference=25,
            max_dte_difference=35,
            **standard_params
        )
        
        # Tighter constraints should yield fewer candidates
        assert len(tight_candidates) <= len(wide_candidates)


class TestCalendarProfitability:
    """Profitability tests for calendars."""
    
    def test_remaining_profit_positive(self, calendar_strategy, calendar_chain, standard_params):
        """Test that all candidates have positive remaining profit."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates:
            assert cand.remaining_profit > 0
    
    def test_time_spread_cost(self, calendar_strategy, calendar_chain, standard_params):
        """Test that time spread cost is positive (far > near)."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates[:10]:
            # For BUY calendars, spread_cost should be positive
            # (buying far-term is more expensive than selling near-term)
            if cand.open_side == "buy":
                assert cand.spread_cost > 0


class TestCalendarActions:
    """Test leg actions (BUY/SELL) are correct for calendars."""
    
    def test_buy_calendar_actions(self, calendar_strategy, calendar_chain, standard_params):
        """Test that BUY calendars have correct actions."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            **standard_params
        )
        
        buy_calendars = [c for c in candidates if c.open_side == "buy"]
        
        for cand in buy_calendars[:5]:
            leg1, leg2 = cand.legs
            
            # For BUY calendar: sell near, buy far
            # Determine which is near vs far
            from datetime import datetime
            exp1 = datetime.strptime(leg1.expiration, "%Y-%m-%d")
            exp2 = datetime.strptime(leg2.expiration, "%Y-%m-%d")
            
            if exp1 < exp2:
                # leg1 is near, leg2 is far
                assert leg1.open_action == "SELL"
                assert leg2.open_action == "BUY"
            else:
                # leg2 is near, leg1 is far
                assert leg2.open_action == "SELL"
                assert leg1.open_action == "BUY"


class TestCalendarMetadata:
    """Test metadata and auxiliary fields."""
    
    def test_expirations_field(self, calendar_strategy, calendar_chain, standard_params):
        """Test that expirations field is populated."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates[:10]:
            # Should have expirations list
            assert hasattr(cand, 'expirations')
            if cand.expirations:
                assert isinstance(cand.expirations, list)
                assert len(cand.expirations) == 2
    
    def test_dte_range_field(self, calendar_strategy, calendar_chain, standard_params):
        """Test that dte_range field is populated."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates[:10]:
            # Should have dte_range tuple
            assert hasattr(cand, 'dte_range')
            if cand.dte_range:
                assert isinstance(cand.dte_range, tuple)
                assert len(cand.dte_range) == 2
                min_dte, max_dte = cand.dte_range
                assert min_dte < max_dte


class TestCalendarStrategyTypeNaming:
    """Test strategy type naming conventions."""
    
    def test_calendar_naming(self, calendar_strategy, calendar_chain, standard_params):
        """Test that calendar strategy types are named correctly."""
        candidates = calendar_strategy.scan(
            chain_data=calendar_chain,
            dte=30,
            **standard_params
        )
        
        for cand in candidates[:20]:
            # Should be CALENDAR or DIAGONAL
            assert "CALENDAR" in cand.strategy_type or "DIAGONAL" in cand.strategy_type
            
            # Should have _BUY or _SELL
            assert "_BUY" in cand.strategy_type or "_SELL" in cand.strategy_type
            
            # Should have _C or _P
            assert cand.strategy_type.endswith("_C") or cand.strategy_type.endswith("_P")
