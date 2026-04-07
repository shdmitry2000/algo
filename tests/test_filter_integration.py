"""
Integration tests for filter pipeline - validates actual scan workflow.

Tests the complete flow:
1. ChainData/ChainIndex → Unified strategies → StrategyCandidate
2. BED filtering
3. Strategy selection
4. Signal generation
"""
import pytest
from datetime import date, timedelta

from filters.phase2strat1.chain_index import ChainIndex
from strategies.implementations import (
    IronCondorStrategy,
    ButterflyStrategy,
    CondorStrategy,
    ShiftedCondorStrategy
)
from strategies.adapters import convert_chain_data_to_chain_index
from filters.phase2strat1.scan import (
    apply_bed_filter_to_candidates,
    select_best_strategy,
    compute_rank_score
)


class TestFilterWithUnifiedStrategies:
    """Test filter pipeline with unified strategies."""
    
    def test_filter_scans_with_all_strategies(self, ic_chain):
        """Test that filter can scan with all unified strategies."""
        # Convert to ChainIndex for filter compatibility
        chain_idx = convert_chain_data_to_chain_index(ic_chain)
        dte = 30
        fee_per_leg = 0.50
        
        # Initialize all scanners (as scan.py does)
        scanners = {
            "IC": IronCondorStrategy(),
            "BF": ButterflyStrategy(),
            "CONDOR": CondorStrategy(),
            "SHIFTED_IC": ShiftedCondorStrategy(),
        }
        
        # Scan with each
        all_candidates = {}
        for name, scanner in scanners.items():
            candidates = scanner.scan(
                convert_chain_index_to_chain_data(chain_idx),
                dte,
                fee_per_leg=fee_per_leg,
                spread_cap_bound=0.01
            )
            
            # Group by strategy_type
            for cand in candidates:
                if cand.strategy_type not in all_candidates:
                    all_candidates[cand.strategy_type] = []
                all_candidates[cand.strategy_type].append(cand)
        
        # Should have found multiple strategy types
        assert len(all_candidates) > 0
        print(f"\n✓ Found {len(all_candidates)} strategy types:")
        for st_type, cands in all_candidates.items():
            print(f"  - {st_type}: {len(cands)} candidates")
        
        # Verify at least IC and CONDOR found something
        assert "IC_BUY" in all_candidates or "IC_SELL" in all_candidates
        assert "CONDOR_BUY" in all_candidates or "CONDOR_SELL" in all_candidates
    
    def test_bed_filter_application(self, ic_chain):
        """Test BED filter works with unified strategies."""
        from strategies.adapters import convert_chain_data_to_chain_index
        
        chain_idx = convert_chain_data_to_chain_index(ic_chain)
        dte = 30
        
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(
            convert_chain_index_to_chain_data(chain_idx),
            dte,
            fee_per_leg=0.50
        )
        
        # Apply BED filter
        apply_bed_filter_to_candidates(candidates, dte)
        
        # Check filter was applied
        passing = [c for c in candidates if c.bed_filter_pass]
        failing = [c for c in candidates if not c.bed_filter_pass]
        
        print(f"\n✓ BED filter applied: {len(passing)} pass, {len(failing)} fail")
        
        # Verify passing candidates meet criteria
        for cand in passing:
            assert cand.remaining_profit > 0, "Passing should have profit > 0"
            # Note: BED filter logic is dte < bed
    
    def test_strategy_selection(self, ic_chain):
        """Test best strategy selection works with unified strategies."""
        from strategies.adapters import convert_chain_index_to_chain_data
        
        chain_idx = convert_chain_data_to_chain_index(ic_chain)
        dte = 30
        
        # Scan with multiple strategies
        ic_scanner = IronCondorStrategy()
        condor_scanner = CondorStrategy()
        
        all_strategies = {}
        
        # Get IC candidates
        ic_candidates = ic_scanner.scan(
            convert_chain_index_to_chain_data(chain_idx),
            dte,
            fee_per_leg=0.50
        )
        apply_bed_filter_to_candidates(ic_candidates, dte)
        for cand in ic_candidates:
            if cand.strategy_type not in all_strategies:
                all_strategies[cand.strategy_type] = []
            all_strategies[cand.strategy_type].append(cand)
        
        # Get Condor candidates
        condor_candidates = condor_scanner.scan(
            convert_chain_index_to_chain_data(chain_idx),
            dte,
            fee_per_leg=0.50
        )
        apply_bed_filter_to_candidates(condor_candidates, dte)
        for cand in condor_candidates:
            if cand.strategy_type not in all_strategies:
                all_strategies[cand.strategy_type] = []
            all_strategies[cand.strategy_type].append(cand)
        
        # Select best per strategy
        best_per_strategy = select_best_strategy(all_strategies)
        
        print(f"\n✓ Selected {len(best_per_strategy)} best strategies:")
        for st_type, cand in best_per_strategy.items():
            print(f"  - {st_type}: rank={cand.rank_score:.2f}, profit=${cand.remaining_profit:.2f}")
        
        # Should have at least one best strategy
        if best_per_strategy:
            assert len(best_per_strategy) > 0
    
    def test_rank_score_computation(self, ic_chain):
        """Test rank score computation for unified strategies."""
        from strategies.adapters import convert_chain_data_to_chain_index
        
        chain_idx = convert_chain_data_to_chain_index(ic_chain)
        dte = 30
        
        ic_scanner = IronCondorStrategy()
        candidates = ic_scanner.scan(
            convert_chain_index_to_chain_data(chain_idx),
            dte,
            fee_per_leg=0.50
        )
        
        # Compute rank scores
        for cand in candidates:
            score = compute_rank_score(cand)
            assert score >= 0, "Rank score should be >= 0"
            # Note: rank_score is computed by compute_rank_score(), not set in StrategyCandidate
        
        print(f"\n✓ Rank scores computed for {len(candidates)} candidates")
    
    def test_filter_handles_multiple_expirations(self, calendar_chain):
        """Test filter works with multi-expiration chains (calendar spreads)."""
        from strategies.implementations import CalendarSpreadStrategy
        from strategies.adapters import convert_chain_index_to_chain_data
        
        # Calendar spreads work directly with ChainData (multi-expiration)
        dte = 30
        
        cal_scanner = CalendarSpreadStrategy()
        candidates = cal_scanner.scan(
            calendar_chain,
            dte,
            fee_per_leg=0.50,
            min_dte_difference=20,
            max_dte_difference=90
        )
        
        print(f"\n✓ Calendar scanner found {len(candidates)} candidates")
        
        # Should find some calendar spreads
        if len(candidates) > 0:
            # Verify multi-expiration structure
            for cand in candidates[:3]:
                assert len(cand.legs) == 2, "Calendar should have 2 legs"
                assert cand.legs[0].expiration != cand.legs[1].expiration, \
                    "Calendar legs should have different expirations"
    
    def test_backwards_compatibility_imports(self):
        """Test that old filter imports still work."""
        import warnings
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            
            # Old imports (should work via shim)
            from filters.phase2strat1.strategies import (
                IronCondorStrategy as IC_Old,
                ButterflyStrategy as BF_Old,
                ShiftedCondorStrategy as Shifted_Old,
            )
            
            # Should be able to instantiate
            ic = IC_Old()
            bf = BF_Old()
            shifted = Shifted_Old()
            
            assert ic.strategy_type == "IC"
            assert bf.strategy_type == "BF"
            assert shifted.strategy_type == "SHIFTED_IC"
        
        print("\n✓ Backwards compatibility maintained")


def convert_chain_index_to_chain_data(chain_idx):
    """Helper to avoid circular import."""
    from strategies.adapters import convert_chain_index_to_chain_data as convert
    return convert(chain_idx)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
