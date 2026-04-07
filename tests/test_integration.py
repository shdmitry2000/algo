"""
Integration tests for filter pipeline with unified strategies.

Tests cover:
- Adapter conversions (ChainIndex <-> ChainData)
- Filter pipeline using new strategies
- Backwards compatibility with legacy code
- End-to-end signal generation
"""
import pytest
from datetime import date, timedelta

from filters.phase2strat1.chain_index import ChainIndex
from strategies.adapters import (
    convert_chain_index_to_chain_data,
    convert_chain_data_to_chain_index
)
from strategies.implementations import (
    IronCondorStrategy,
    ButterflyStrategy,
    CondorStrategy,
    ShiftedCondorStrategy
)


class TestChainIndexAdapter:
    """Test ChainIndex <-> ChainData conversion."""
    
    def test_chain_index_to_chain_data(self, ic_chain):
        """Test converting unified ChainData back to legacy ChainIndex."""
        from tests.fixtures.synthetic_chains import StandardOptionTick
        
        # Create a simple ChainIndex from ChainData ticks
        ticks = ic_chain.ticks
        expiration = ic_chain.expirations[0]
        symbol = ic_chain.symbol
        
        chain_idx = ChainIndex(symbol, expiration, ticks)
        
        # Convert to ChainData
        chain_data = convert_chain_index_to_chain_data(chain_idx)
        
        # Verify conversion
        assert chain_data.symbol == symbol
        assert expiration in chain_data.expirations
        assert len(chain_data.sorted_strikes()) > 0
        
        # Verify we can get options
        strikes = chain_data.sorted_strikes()
        test_strike = strikes[len(strikes) // 2]
        
        call = chain_data.get_call(test_strike)
        put = chain_data.get_put(test_strike)
        
        assert call is not None
        assert put is not None
        assert call.strike == test_strike
        assert put.strike == test_strike
    
    def test_chain_data_to_chain_index(self, ic_chain):
        """Test converting ChainData to ChainIndex."""
        # Convert to ChainIndex (adapter extracts first expiration automatically)
        chain_idx = convert_chain_data_to_chain_index(ic_chain)
        
        # Verify conversion
        assert chain_idx.symbol == ic_chain.symbol
        assert chain_idx.expiration in ic_chain.expirations
        
        # Verify we can get options
        strikes = chain_idx.sorted_strikes()
        assert len(strikes) > 0
        
        test_strike = strikes[len(strikes) // 2]
        call = chain_idx.get_call(test_strike)
        put = chain_idx.get_put(test_strike)
        
        assert call is not None
        assert put is not None
    
    def test_round_trip_conversion(self, ic_chain):
        """Test ChainData -> ChainIndex -> ChainData preserves data."""
        from tests.fixtures.synthetic_chains import StandardOptionTick
        
        original_data = ic_chain
        
        # Convert to ChainIndex (uses first expiration)
        chain_idx = convert_chain_data_to_chain_index(original_data)
        
        # Convert back to ChainData
        restored_data = convert_chain_index_to_chain_data(chain_idx)
        
        # Verify key properties preserved
        assert restored_data.symbol == original_data.symbol
        assert len(restored_data.sorted_strikes()) == len(original_data.sorted_strikes())
        # Note: spot_price is not preserved through ChainIndex (it doesn't store it)
        # This is a known limitation of the legacy ChainIndex


class TestFilterPipelineIntegration:
    """Test filter pipeline with unified strategies."""
    
    def test_strategies_scan_with_chain_data(self, ic_chain, standard_params):
        """Test that all strategies can scan with ChainData."""
        ic_scanner = IronCondorStrategy()
        bf_scanner = ButterflyStrategy()
        condor_scanner = CondorStrategy()
        shifted_scanner = ShiftedCondorStrategy()
        
        dte = 30
        
        # All should scan successfully
        ic_results = ic_scanner.scan(ic_chain, dte, **standard_params)
        bf_results = bf_scanner.scan(ic_chain, dte, **standard_params)
        condor_results = condor_scanner.scan(ic_chain, dte, **standard_params)
        shifted_results = shifted_scanner.scan(ic_chain, dte, **standard_params)
        
        # Should all find some candidates
        assert len(ic_results) > 0
        # BF may have 0 (needs exact equidistant strikes)
        assert len(condor_results) > 0
        # Shifted may have 0 (needs different strike combinations)
    
    def test_strategies_work_with_legacy_chain_index(self, ic_chain):
        """Test that strategies work when ChainIndex is converted to ChainData."""
        from tests.fixtures.synthetic_chains import StandardOptionTick
        
        # Create ChainIndex from ChainData ticks
        ticks = ic_chain.ticks
        expiration = ic_chain.expirations[0]
        chain_idx = ChainIndex(ic_chain.symbol, expiration, ticks)
        
        # Convert to ChainData
        chain_data = convert_chain_index_to_chain_data(chain_idx)
        
        # Scan with unified strategy
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(
            chain_data,
            dte=30,
            fee_per_leg=0.50,
            spread_cap_bound=0.01
        )
        
        # Should work and find candidates
        assert len(candidates) > 0
        
        # Verify candidate structure
        assert candidates[0].symbol == ic_chain.symbol


class TestBackwardsCompatibility:
    """Test backwards compatibility with old imports."""
    
    def test_old_imports_still_work(self):
        """Test that old import paths still work (with deprecation)."""
        import warnings
        
        # Suppress deprecation warnings for this test
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            
            # Old imports should still work
            from filters.phase2strat1.strategies import (
                IronCondorStrategy as IC_Old,
                ButterflyStrategy as BF_Old,
                BaseStrategy,
                StrategyCandidate
            )
            
            # New imports
            from strategies.implementations import (
                IronCondorStrategy as IC_New,
                ButterflyStrategy as BF_New
            )
            from strategies.core import (
                BaseStrategy as Base_New,
                StrategyCandidate as Candidate_New
            )
            
            # Should be the same classes
            assert IC_Old == IC_New
            assert BF_Old == BF_New
            assert BaseStrategy == Base_New
            assert StrategyCandidate == Candidate_New
    
    def test_scan_module_imports(self):
        """Test that scan.py can still be imported."""
        from filters.phase2strat1.scan import (
            run_scan,
            build_strategy_snapshot,
            apply_bed_filter_to_candidates,
            compute_rank_score,
            select_best_strategy
        )
        
        # Should import without errors
        assert run_scan is not None
        assert build_strategy_snapshot is not None


class TestEndToEndCandidateFlow:
    """Test end-to-end candidate generation and filtering."""
    
    def test_candidate_generation_and_bed_filter(self, ic_chain, standard_params):
        """Test full flow: scan -> BED filter -> select best."""
        from filters.phase2strat1.scan import (
            apply_bed_filter_to_candidates,
            select_best_strategy
        )
        
        ic_scanner = IronCondorStrategy()
        dte = 30
        
        # Generate candidates
        candidates = ic_scanner.scan(ic_chain, dte, **standard_params)
        assert len(candidates) > 0
        
        # Apply BED filter
        apply_bed_filter_to_candidates(candidates, dte)
        
        # Some should pass
        passing = [c for c in candidates if c.bed_filter_pass]
        
        # Check BED logic (BED < DTE should pass)
        for cand in passing:
            # BED filter marks as pass when remaining_profit > 0 and DTE < BED
            # (meaning we break even before expiration)
            assert cand.remaining_profit > 0
    
    def test_multi_strategy_selection(self, ic_chain, standard_params):
        """Test selecting best strategy across multiple strategy types."""
        from filters.phase2strat1.scan import (
            apply_bed_filter_to_candidates,
            select_best_strategy
        )
        
        ic_scanner = IronCondorStrategy()
        condor_scanner = CondorStrategy()
        dte = 30
        
        # Generate candidates from multiple strategies
        all_strategies = {}
        
        ic_candidates = ic_scanner.scan(ic_chain, dte, **standard_params)
        apply_bed_filter_to_candidates(ic_candidates, dte)
        for cand in ic_candidates:
            if cand.strategy_type not in all_strategies:
                all_strategies[cand.strategy_type] = []
            all_strategies[cand.strategy_type].append(cand)
        
        condor_candidates = condor_scanner.scan(ic_chain, dte, **standard_params)
        apply_bed_filter_to_candidates(condor_candidates, dte)
        for cand in condor_candidates:
            if cand.strategy_type not in all_strategies:
                all_strategies[cand.strategy_type] = []
            all_strategies[cand.strategy_type].append(cand)
        
        # Select best per strategy
        best_per_strategy = select_best_strategy(all_strategies)
        
        # Should have at least one best strategy
        if best_per_strategy:
            assert len(best_per_strategy) > 0
            
            # Each selected candidate should have passed BED
            for strategy_type, candidate in best_per_strategy.items():
                assert candidate.bed_filter_pass is True


class TestStrategySnapshot:
    """Test strategy snapshot building for signals."""
    
    def test_build_strategy_snapshot(self, ic_chain, standard_params):
        """Test building minimal chain snapshot with only used strikes."""
        from filters.phase2strat1.scan import build_strategy_snapshot
        
        ic_scanner = IronCondorStrategy()
        dte = 30
        
        # Generate candidates
        candidates = ic_scanner.scan(ic_chain, dte, **standard_params)
        
        # Build dict by strategy type
        strategies = {}
        for cand in candidates[:3]:  # Take first 3
            strategies[cand.strategy_type] = cand
        
        # Build snapshot
        snapshot = build_strategy_snapshot(strategies, ic_chain.ticks)
        
        # Verify snapshot structure
        assert "chain" in snapshot
        assert "strategies" in snapshot
        
        # Chain should be filtered to only used strikes
        assert isinstance(snapshot["chain"], list)
        assert len(snapshot["chain"]) > 0
        
        # Strategies should be serialized
        assert len(snapshot["strategies"]) == len(strategies)


class TestMultiExpirationSupport:
    """Test that Calendar spreads work in filter context."""
    
    def test_calendar_with_adapter(self, calendar_chain, standard_params):
        """Test Calendar strategy with multi-expiration data."""
        from strategies.implementations import CalendarSpreadStrategy
        
        cal_scanner = CalendarSpreadStrategy()
        dte = 30
        
        # Should scan multi-expiration chain
        candidates = cal_scanner.scan(
            calendar_chain, dte,
            min_dte_difference=20,
            max_dte_difference=90,
            **standard_params
        )
        
        # Should find calendar candidates
        assert len(candidates) > 0
        
        # Verify multi-expiration structure
        for cand in candidates[:5]:
            # Calendar should have 2 legs with different expirations
            assert len(cand.legs) == 2
            assert cand.legs[0].expiration != cand.legs[1].expiration


class TestStrategyRegistry:
    """Test that registry works with all strategies."""
    
    def test_all_strategies_registered(self):
        """Test that all implemented strategies are in registry."""
        from strategies.core import STRATEGY_TYPES, get_strategy_class
        
        # Check key strategies are registered
        key_types = [
            "IC_BUY", "BF_BUY", "CONDOR_BUY", "SHIFTED_IC_BUY",
            "FLYGONAAL_BUY", "CALENDAR_BUY_C"
        ]
        
        for strategy_type in key_types:
            assert strategy_type in STRATEGY_TYPES
            
            # Should be able to get class
            strategy_class = get_strategy_class(strategy_type)
            assert strategy_class is not None
    
    def test_strategy_instantiation_from_registry(self):
        """Test instantiating strategies from registry."""
        from strategies.core import get_strategy_class
        
        # Get class from registry
        IC_class = get_strategy_class("IC_BUY")
        BF_class = get_strategy_class("BF_BUY")
        Condor_class = get_strategy_class("CONDOR_BUY")
        
        # Instantiate
        ic = IC_class()
        bf = BF_class()
        condor = Condor_class()
        
        # Verify types
        assert ic.strategy_type == "IC"
        assert bf.strategy_type == "BF"
        assert condor.strategy_type == "CONDOR"
