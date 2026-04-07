"""
Unit tests for Flygonaal (3:2:2:3) strategy implementation.

Tests cover:
- Standard 3:2:2:3 configuration
- Imbalanced variants (4:3, 5:3, etc.)
- Wing width constraints
- Edge cases specific to this multi-wing strategy
"""
import pytest
from strategies.implementations import FlygonaalStrategy
from strategies.core import get_strategy_class


class TestFlygonaalBasic:
    """Basic functionality tests for Flygonaal."""
    
    def test_strategy_type(self, flygonaal_strategy):
        """Test strategy type property."""
        assert flygonaal_strategy.strategy_type == "FLYGONAAL"
    
    def test_registry_integration(self):
        """Test strategy is properly registered."""
        strategy_class = get_strategy_class("FLYGONAAL_BUY")
        assert strategy_class is not None
        assert strategy_class == FlygonaalStrategy
    
    def test_scan_basic(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test basic Flygonaal scan generates candidates."""
        dte = 45
        
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=dte,
            **standard_params
        )
        
        # Should find at least some candidates
        assert len(candidates) > 0
        
        # Check first candidate structure
        cand = candidates[0]
        assert cand.symbol == flygonaal_chain.symbol
        assert cand.dte == dte
        assert cand.leg_count == 4
        assert len(cand.legs) == 4
        assert "FLYGONAAL" in cand.strategy_type
    
    def test_leg_structure_standard(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that standard 3:2:2:3 candidates have correct leg structure."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            include_imbalanced=False,
            **standard_params
        )
        
        for cand in candidates[:5]:
            # 4 legs
            assert len(cand.legs) == 4
            
            # Leg 1 (Put K_A): quantity 3
            # Leg 2 (Put K_B): quantity 2
            # Leg 3 (Call K_C): quantity 2
            # Leg 4 (Call K_D): quantity 3
            
            leg1, leg2, leg3, leg4 = cand.legs
            
            # Check rights
            assert leg1.right == "P"
            assert leg2.right == "P"
            assert leg3.right == "C"
            assert leg4.right == "C"
            
            # Check quantities for standard (3:2:2:3)
            if not cand.is_imbalanced:
                assert leg1.quantity == 3
                assert leg2.quantity == 2
                assert leg3.quantity == 2
                assert leg4.quantity == 3
            
            # Check strikes ascending
            assert leg1.strike < leg2.strike < leg3.strike < leg4.strike
    
    def test_four_unique_strikes(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that Flygonaal uses 4 unique strikes."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            **standard_params
        )
        
        for cand in candidates[:10]:
            # Should have 4 unique strikes
            assert len(cand.strikes_used) == 4
            
            # Strikes should be in ascending order
            assert cand.strikes_used == sorted(cand.strikes_used)


class TestFlygonaalWingWidths:
    """Wing width constraint tests."""
    
    def test_wing_width_constraints(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that wing widths are within min/max bounds."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            min_wing_width=5.0,
            max_wing_width=20.0,
            **standard_params
        )
        
        for cand in candidates:
            # Get the 4 strikes
            K_A, K_B, K_C, K_D = cand.strikes_used
            
            put_wing_width = K_B - K_A
            call_wing_width = K_D - K_C
            
            # Check constraints
            assert 5.0 <= put_wing_width <= 20.0
            assert 5.0 <= call_wing_width <= 20.0
    
    def test_narrow_wings_reduce_candidates(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that narrower wing width constraints reduce candidates."""
        wide_candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            min_wing_width=5.0,
            max_wing_width=50.0,
            **standard_params
        )
        
        narrow_candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            min_wing_width=10.0,
            max_wing_width=15.0,
            **standard_params
        )
        
        # Narrower constraints should yield fewer candidates
        assert len(narrow_candidates) < len(wide_candidates)


class TestFlygonaalImbalanced:
    """Imbalanced quantity tests for Flygonaal."""
    
    def test_imbalanced_generation(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that imbalanced variants are generated."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            include_imbalanced=True,
            **standard_params
        )
        
        imbalanced = [c for c in candidates if c.is_imbalanced]
        standard = [c for c in candidates if not c.is_imbalanced]
        
        # Should have both standard and imbalanced
        assert len(standard) > 0
        assert len(imbalanced) > 0
    
    def test_imbalanced_ratios(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that imbalanced candidates have valid ratios."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            include_imbalanced=True,
            **standard_params
        )
        
        imbalanced = [c for c in candidates if c.is_imbalanced]
        
        for cand in imbalanced[:10]:
            # Get outer and inner quantities
            outer_qty = cand.legs[0].quantity  # Outer wings
            inner_qty = cand.legs[1].quantity  # Inner wings
            
            # Outer should be greater than inner (e.g., 4:3, 5:3, etc.)
            assert outer_qty > inner_qty
            
            # Total legs should respect max constraint (default 16)
            total_legs = 2 * (outer_qty + inner_qty)
            assert total_legs <= 16
    
    def test_max_legs_constraint(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that max_imbalanced_legs constraint is respected."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            include_imbalanced=True,
            max_imbalanced_legs=12,
            **standard_params
        )
        
        for cand in candidates:
            assert cand.total_quantity <= 12


class TestFlygonaalProfitability:
    """Profitability tests specific to Flygonaal."""
    
    def test_remaining_profit_positive(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that all candidates have positive remaining profit."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            **standard_params
        )
        
        for cand in candidates:
            assert cand.remaining_profit > 0
    
    def test_notional_calculation(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test buy and sell notional calculations."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            **standard_params
        )
        
        for cand in candidates[:10]:
            # buy_notional = outer_qty * (put_wing + call_wing)
            # sell_notional = inner_qty * (put_wing + call_wing)
            
            K_A, K_B, K_C, K_D = cand.strikes_used
            outer_qty = cand.legs[0].quantity
            inner_qty = cand.legs[1].quantity
            
            put_wing_width = K_B - K_A
            call_wing_width = K_D - K_C
            
            expected_buy = outer_qty * (put_wing_width + call_wing_width)
            expected_sell = inner_qty * (put_wing_width + call_wing_width)
            
            assert cand.buy_notional == expected_buy
            assert cand.sell_notional == expected_sell
    
    def test_buy_exceeds_sell_notional(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that buy_notional >= sell_notional (safety check)."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            **standard_params
        )
        
        for cand in candidates:
            # Outer qty should be >= inner qty, so buy notional >= sell notional
            assert cand.buy_notional >= cand.sell_notional


class TestFlygonaalActions:
    """Test leg actions (BUY/SELL) are correct."""
    
    def test_standard_actions(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that standard Flygonaal has correct BUY/SELL actions."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            include_imbalanced=False,
            **standard_params
        )
        
        for cand in candidates[:5]:
            leg1, leg2, leg3, leg4 = cand.legs
            
            # Standard structure:
            # Leg 1 (outer put): BUY
            # Leg 2 (inner put): SELL
            # Leg 3 (inner call): SELL
            # Leg 4 (outer call): BUY
            
            assert leg1.open_action == "BUY"
            assert leg2.open_action == "SELL"
            assert leg3.open_action == "SELL"
            assert leg4.open_action == "BUY"


class TestFlygonaalEdgeCases:
    """Edge case tests."""
    
    def test_insufficient_strikes(self, flygonaal_strategy, narrow_range, standard_params):
        """Test behavior with insufficient strikes."""
        candidates = flygonaal_strategy.scan(
            chain_data=narrow_range,
            dte=30,
            min_wing_width=5.0,
            **standard_params
        )
        
        # May have very few or no candidates due to narrow range
        # But shouldn't crash
        assert isinstance(candidates, list)
    
    def test_high_fees_impact(self, flygonaal_strategy, flygonaal_chain, high_fee_params):
        """Test that high fees reduce candidates (due to higher leg count)."""
        std_candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            fee_per_leg=0.50,
            spread_cap_bound=0.01,
            min_liquidity_bid=0.05,
            min_liquidity_ask=0.05,
        )
        
        high_fee_candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            **high_fee_params
        )
        
        # Flygonaal has total_quantity = 2*(3+2) = 10 contracts for standard
        # So fees impact is significant
        assert len(high_fee_candidates) < len(std_candidates)


class TestFlygonaalMetadata:
    """Test metadata and auxiliary fields."""
    
    def test_strategy_type_naming(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test strategy type naming conventions."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            include_imbalanced=True,
            **standard_params
        )
        
        for cand in candidates[:20]:
            # Should start with FLYGONAAL
            assert cand.strategy_type.startswith("FLYGONAAL")
            
            # Should have _BUY or _SELL
            assert "_BUY" in cand.strategy_type or "_SELL" in cand.strategy_type
            
            # Imbalanced should have _IMBAL suffix
            if cand.is_imbalanced:
                assert "_IMBAL" in cand.strategy_type
    
    def test_raw_spreads_metadata(self, flygonaal_strategy, flygonaal_chain, standard_params):
        """Test that raw_spreads contains expected keys."""
        candidates = flygonaal_strategy.scan(
            chain_data=flygonaal_chain,
            dte=45,
            **standard_params
        )
        
        for cand in candidates[:5]:
            # Should have per-wing spreads
            assert "put_wing" in cand.raw_spreads
            assert "call_wing" in cand.raw_spreads
            assert "outer_qty" in cand.raw_spreads
            assert "inner_qty" in cand.raw_spreads
            
            # Quantities should match legs
            assert cand.raw_spreads["outer_qty"] == cand.legs[0].quantity
            assert cand.raw_spreads["inner_qty"] == cand.legs[1].quantity
