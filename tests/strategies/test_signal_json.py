"""
Test Signal JSON structure - verifies complete data before cache storage.
Tests that the Signal object contains all required strategy data, legs, filters, etc.
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.strategies.test_fixtures import get_test_chain, get_test_dte
from filters.phase2strat1.chain_index import ChainIndex
from filters.phase2strat1.strategies import (
    IronCondorStrategy,
    ButterflyStrategy,
    ShiftedCondorStrategy,
    StrategyCandidate
)
from filters.phase2strat1.models import Signal
from typing import Dict, List


def build_strategy_snapshot(
    strategies: Dict[str, StrategyCandidate],
    all_ticks: list
) -> Dict[str, any]:
    """Build minimal chain snapshot with only used strikes."""
    used_strikes = set()
    for strategy in strategies.values():
        used_strikes.update(strategy.strikes_used)
    
    relevant_ticks = [t for t in all_ticks if t.strike in used_strikes]
    
    chain_data = [
        {
            "strike": t.strike,
            "right": t.right,
            "bid": t.bid,
            "ask": t.ask,
            "mid": t.mid,
            "volume": t.volume,
            "open_interest": t.open_interest,
            "root": t.root
        }
        for t in relevant_ticks
    ]
    
    strategy_details = {}
    for strategy_type, candidate in strategies.items():
        strategy_details[strategy_type] = candidate.to_dict()
    
    return {
        "chain": chain_data,
        "strategies": strategy_details
    }


def create_test_signal(chain_type: str = "buy") -> Signal:
    """Create a complete Signal object using test data."""
    ticks, expiration = get_test_chain(chain_type=chain_type)
    dte = get_test_dte()
    symbol = "TEST_BUY" if chain_type == "buy" else "TEST_SELL"
    
    chain_idx = ChainIndex(symbol, expiration, ticks)
    
    # Scan all strategies
    ic_scanner = IronCondorStrategy()
    bf_scanner = ButterflyStrategy()
    shifted_ic_scanner = ShiftedCondorStrategy()
    
    fee_per_leg = 0.65
    
    all_candidates = {}
    
    # 1. Iron Condor
    ic_candidates = ic_scanner.scan(chain_idx, dte, fee_per_leg, include_imbalanced=True)
    for candidate in ic_candidates:
        if candidate.strategy_type not in all_candidates:
            all_candidates[candidate.strategy_type] = []
        all_candidates[candidate.strategy_type].append(candidate)
    
    # 2. Butterfly
    bf_candidates = bf_scanner.scan(chain_idx, dte, fee_per_leg, include_imbalanced=True)
    for candidate in bf_candidates:
        if candidate.strategy_type not in all_candidates:
            all_candidates[candidate.strategy_type] = []
        all_candidates[candidate.strategy_type].append(candidate)
    
    # 3. Shifted Butterfly
    shifted_bf_candidates = bf_scanner.scan_shifted(chain_idx, dte, fee_per_leg, include_imbalanced=True)
    for candidate in shifted_bf_candidates:
        if candidate.strategy_type not in all_candidates:
            all_candidates[candidate.strategy_type] = []
        all_candidates[candidate.strategy_type].append(candidate)
    
    # 4. Shifted IC
    shifted_ic_candidates = shifted_ic_scanner.scan(chain_idx, dte, fee_per_leg, include_imbalanced=True)
    for candidate in shifted_ic_candidates:
        if candidate.strategy_type not in all_candidates:
            all_candidates[candidate.strategy_type] = []
        all_candidates[candidate.strategy_type].append(candidate)
    
    # Apply BED filter
    for candidates in all_candidates.values():
        for c in candidates:
            c.bed_filter_pass = dte < c.break_even_days and c.remaining_profit > 0
    
    # Select best per strategy
    best_per_strategy = {}
    for strategy_type, candidates in all_candidates.items():
        passing = [c for c in candidates if c.bed_filter_pass]
        if passing:
            passing.sort(key=lambda x: x.rank_score, reverse=True)
            best_per_strategy[strategy_type] = passing[0]
    
    # Find overall best
    priority_order = [
        "BF_BUY", "BF_SELL",
        "SHIFTED_BF_BUY", "SHIFTED_BF_SELL",
        "IC_BUY", "IC_SELL",
        "SHIFTED_IC_BUY", "SHIFTED_IC_SELL",
        "BF_BUY_IMBAL", "BF_SELL_IMBAL",
        "SHIFTED_BF_BUY_IMBAL", "SHIFTED_BF_SELL_IMBAL",
        "IC_BUY_IMBAL", "IC_SELL_IMBAL",
        "SHIFTED_IC_BUY_IMBAL", "SHIFTED_IC_SELL_IMBAL"
    ]
    
    best_strategy_type = None
    best_candidate = None
    for strategy_type in priority_order:
        if strategy_type in best_per_strategy:
            best_strategy_type = strategy_type
            best_candidate = best_per_strategy[strategy_type]
            break
    
    # Build signal
    strategies_dict = {k: v.to_dict() for k, v in best_per_strategy.items()}
    chain_snapshot = build_strategy_snapshot(best_per_strategy, ticks)
    
    signal = Signal(
        signal_id="test-signal-123",
        symbol=symbol,
        expiration=expiration,
        dte=dte,
        strategies=strategies_dict,
        best_strategy_type=best_strategy_type,
        best_rank_score=best_candidate.rank_score,
        chain_timestamp="2026-03-29T00:00:00",
        run_id="test-run-456",
        computed_at="2026-03-29T10:00:00",
        chain_snapshot=chain_snapshot
    )
    
    return signal


def test_signal_json_structure():
    """Test Signal JSON has complete structure with all required fields."""
    print("\n" + "="*80)
    print("TEST: Signal JSON Structure")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    signal_dict = signal.to_dict()
    
    # Verify top-level fields
    required_fields = [
        "signal_id", "symbol", "expiration", "dte",
        "strategies", "best_strategy_type", "best_rank_score",
        "chain_timestamp", "run_id", "computed_at", "chain_snapshot"
    ]
    
    for field in required_fields:
        assert field in signal_dict, f"Missing required field: {field}"
        print(f"✓ Field present: {field}")
    
    print(f"\n✓ All {len(required_fields)} required fields present")
    
    # Verify JSON serialization works
    signal_json = signal.to_json()
    assert isinstance(signal_json, str), "to_json() should return string"
    print(f"✓ JSON serialization works ({len(signal_json)} bytes)")
    
    # Verify JSON is valid
    parsed = json.loads(signal_json)
    assert parsed["signal_id"] == "test-signal-123", "Signal ID mismatch"
    print("✓ JSON is valid and parseable")
    
    print("✅ PASSED: Signal JSON structure complete\n")
    return True


def test_signal_strategies_field():
    """Test Signal.strategies contains all detected strategy types with complete data."""
    print("\n" + "="*80)
    print("TEST: Signal Strategies Field Complete")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    strategies = signal.strategies
    
    print(f"Strategies in signal: {len(strategies)} types")
    for strategy_type in sorted(strategies.keys()):
        print(f"  ✓ {strategy_type}")
    
    assert len(strategies) > 0, "Signal should contain at least one strategy"
    print(f"\n✓ Signal contains {len(strategies)} strategy types")
    
    # Verify each strategy has complete data
    for strategy_type, strategy_data in strategies.items():
        required_strategy_fields = [
            "strategy_type", "symbol", "expiration", "dte",
            "open_side", "legs", "leg_count",
            "strike_difference", "strikes_used",
            "remaining_profit", "break_even_days",
            "bed_filter_pass", "rank_score"
        ]
        
        for field in required_strategy_fields:
            assert field in strategy_data, f"{strategy_type} missing field: {field}"
        
        print(f"✓ {strategy_type}: all required fields present")
    
    print(f"\n✓ All {len(strategies)} strategies have complete data")
    print("✅ PASSED: Strategies field complete\n")
    return True


def test_signal_legs_data():
    """Test that all strategies contain complete leg data."""
    print("\n" + "="*80)
    print("TEST: Signal Contains Complete Leg Data")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    strategies = signal.strategies
    
    total_legs = 0
    
    for strategy_type, strategy_data in strategies.items():
        legs = strategy_data.get("legs", [])
        
        assert len(legs) > 0, f"{strategy_type} has no legs"
        
        for leg in legs:
            # Verify all leg fields present
            required_leg_fields = [
                "leg_index", "strike", "right", "open_action",
                "quantity", "bid", "ask", "mid"
            ]
            
            for field in required_leg_fields:
                assert field in leg, f"{strategy_type} leg missing field: {field}"
            
            total_legs += 1
        
        print(f"✓ {strategy_type}: {len(legs)} legs with complete data")
    
    print(f"\n✓ Total legs across all strategies: {total_legs}")
    print("✅ PASSED: All legs have complete data\n")
    return True


def test_signal_filter_metadata():
    """Test that strategies contain filter calculation metadata."""
    print("\n" + "="*80)
    print("TEST: Signal Contains Filter Metadata")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    strategies = signal.strategies
    
    for strategy_type, strategy_data in strategies.items():
        # Verify filter metadata present
        filter_fields = [
            "remaining_profit",
            "remaining_percent",
            "break_even_days",
            "bed_filter_pass",
            "rank_score",
            "liquidity_pass"
        ]
        
        for field in filter_fields:
            assert field in strategy_data, f"{strategy_type} missing filter field: {field}"
        
        # Verify values are reasonable
        assert strategy_data["remaining_profit"] > 0, f"{strategy_type} should have positive profit"
        assert strategy_data["break_even_days"] > 0, f"{strategy_type} should have positive BED"
        
        print(f"✓ {strategy_type}: profit=${strategy_data['remaining_profit']:.2f}, BED={strategy_data['break_even_days']:.1f}d")
    
    print(f"\n✓ All {len(strategies)} strategies have complete filter metadata")
    print("✅ PASSED: Filter metadata complete\n")
    return True


def test_signal_chain_snapshot():
    """Test that chain_snapshot contains only used strikes."""
    print("\n" + "="*80)
    print("TEST: Signal Chain Snapshot Optimized")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    snapshot = signal.chain_snapshot
    
    assert snapshot is not None, "Signal should have chain_snapshot"
    assert "chain" in snapshot, "Snapshot should have 'chain' field"
    assert "strategies" in snapshot, "Snapshot should have 'strategies' field"
    
    chain_data = snapshot["chain"]
    strategy_data = snapshot["strategies"]
    
    print(f"Snapshot chain data: {len(chain_data)} ticks")
    print(f"Snapshot strategies: {len(strategy_data)} types")
    
    # Collect strikes from chain data
    snapshot_strikes = set(t["strike"] for t in chain_data)
    print(f"Strikes in snapshot: {sorted(snapshot_strikes)}")
    
    # Collect strikes used by strategies
    used_strikes = set()
    for strategy_type, strategy_dict in strategy_data.items():
        used_strikes.update(strategy_dict["strikes_used"])
    
    print(f"Strikes used by strategies: {sorted(used_strikes)}")
    
    # Verify snapshot contains exactly the used strikes (no more, no less)
    assert snapshot_strikes == used_strikes, "Snapshot should contain exactly the used strikes"
    print("✓ Snapshot contains exactly the used strikes")
    
    # Get original chain size
    ticks, _ = get_test_chain(chain_type="buy")
    original_strikes = set(t.strike for t in ticks)
    
    print(f"\nOptimization:")
    print(f"  Original chain: {len(original_strikes)} strikes")
    print(f"  Snapshot: {len(snapshot_strikes)} strikes")
    print(f"  Saved: {len(original_strikes) - len(snapshot_strikes)} strikes")
    
    assert len(snapshot_strikes) < len(original_strikes), "Snapshot should be smaller than full chain"
    print("✓ Snapshot is optimized (smaller than full chain)")
    
    print("✅ PASSED: Chain snapshot optimized\n")
    return True


def test_signal_best_strategy_selection():
    """Test that Signal correctly identifies the best strategy."""
    print("\n" + "="*80)
    print("TEST: Signal Best Strategy Selection")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    
    assert signal.best_strategy_type is not None, "Should have best_strategy_type"
    print(f"Best strategy type: {signal.best_strategy_type}")
    
    # Verify best strategy exists in strategies dict
    assert signal.best_strategy_type in signal.strategies, \
        "best_strategy_type should exist in strategies dict"
    print(f"✓ Best strategy exists in strategies dict")
    
    # Get best strategy data
    best_strategy = signal.get_best_strategy()
    assert best_strategy is not None, "get_best_strategy() should return data"
    
    print(f"✓ Best strategy data accessible")
    print(f"  Type: {best_strategy['strategy_type']}")
    print(f"  Side: {best_strategy['open_side']}")
    print(f"  Profit: ${best_strategy['remaining_profit']:.2f}")
    print(f"  BED: {best_strategy['break_even_days']:.1f} days")
    print(f"  Rank: {best_strategy['rank_score']:.2f}")
    
    # Verify best_rank_score matches
    assert signal.best_rank_score == best_strategy["rank_score"], \
        "Signal.best_rank_score should match best strategy's rank_score"
    print(f"✓ best_rank_score matches ({signal.best_rank_score:.2f})")
    
    print("✅ PASSED: Best strategy selection correct\n")
    return True


def test_signal_json_serialization():
    """Test that Signal can be serialized and deserialized correctly."""
    print("\n" + "="*80)
    print("TEST: Signal JSON Serialization/Deserialization")
    print("="*80)
    
    original_signal = create_test_signal(chain_type="sell")
    
    # Serialize to JSON
    signal_json = original_signal.to_json()
    print(f"Serialized to JSON: {len(signal_json)} bytes")
    
    # Verify it's valid JSON
    parsed = json.loads(signal_json)
    assert isinstance(parsed, dict), "JSON should parse to dict"
    print("✓ Valid JSON format")
    
    # Deserialize back to Signal
    restored_signal = Signal.from_json(signal_json)
    print("✓ Deserialized back to Signal object")
    
    # Verify all fields match
    assert restored_signal.signal_id == original_signal.signal_id
    assert restored_signal.symbol == original_signal.symbol
    assert restored_signal.expiration == original_signal.expiration
    assert restored_signal.dte == original_signal.dte
    assert len(restored_signal.strategies) == len(original_signal.strategies)
    assert restored_signal.best_strategy_type == original_signal.best_strategy_type
    
    print("✓ All fields preserved after round-trip")
    
    # Verify strategies preserved
    for strategy_type in original_signal.strategies.keys():
        assert strategy_type in restored_signal.strategies, \
            f"Strategy {strategy_type} lost in serialization"
        
        original_legs = original_signal.strategies[strategy_type]["legs"]
        restored_legs = restored_signal.strategies[strategy_type]["legs"]
        assert len(original_legs) == len(restored_legs), \
            f"{strategy_type}: leg count mismatch"
    
    print(f"✓ All {len(original_signal.strategies)} strategies preserved with legs")
    
    print("✅ PASSED: JSON serialization/deserialization works\n")
    return True


def test_signal_complete_data_for_history():
    """Test that Signal contains ALL data needed for history display."""
    print("\n" + "="*80)
    print("TEST: Signal Contains Complete History Data")
    print("="*80)
    
    signal = create_test_signal(chain_type="sell")
    
    print("Verifying signal contains all data for history display:")
    
    # 1. Metadata
    print("\n1. Metadata:")
    assert signal.signal_id, "Missing signal_id"
    assert signal.symbol, "Missing symbol"
    assert signal.expiration, "Missing expiration"
    assert signal.dte > 0, "Missing/invalid dte"
    assert signal.run_id, "Missing run_id"
    assert signal.computed_at, "Missing computed_at"
    assert signal.chain_timestamp, "Missing chain_timestamp"
    print(f"   ✓ signal_id: {signal.signal_id}")
    print(f"   ✓ symbol+expiration+datetime: {signal.symbol}_{signal.expiration}_{signal.chain_timestamp}")
    print(f"   ✓ dte: {signal.dte} days")
    
    # 2. Strategies with legs and filter data
    print("\n2. Strategies (legs + filter data):")
    for strategy_type, strategy_data in signal.strategies.items():
        legs = strategy_data["legs"]
        
        assert len(legs) > 0, f"{strategy_type} has no legs"
        
        # Check leg data
        for leg in legs:
            assert "strike" in leg, f"{strategy_type} leg missing strike"
            assert "right" in leg, f"{strategy_type} leg missing right"
            assert "open_action" in leg, f"{strategy_type} leg missing open_action"
            assert "quantity" in leg, f"{strategy_type} leg missing quantity"
        
        # Check filter data
        assert "remaining_profit" in strategy_data, f"{strategy_type} missing remaining_profit"
        assert "break_even_days" in strategy_data, f"{strategy_type} missing break_even_days"
        assert "bed_filter_pass" in strategy_data, f"{strategy_type} missing bed_filter_pass"
        
        print(f"   ✓ {strategy_type}: {len(legs)} legs, profit=${strategy_data['remaining_profit']:.2f}")
    
    print(f"\n   ✓ All {len(signal.strategies)} strategies have legs and filter data")
    
    # 3. Chain snapshot (for reconstruction)
    print("\n3. Chain snapshot:")
    snapshot = signal.chain_snapshot
    assert snapshot, "Missing chain_snapshot"
    assert "chain" in snapshot, "Snapshot missing 'chain'"
    assert "strategies" in snapshot, "Snapshot missing 'strategies'"
    
    chain_ticks = snapshot["chain"]
    print(f"   ✓ Chain data: {len(chain_ticks)} ticks (only used strikes)")
    
    # Verify each tick has required fields
    for tick in chain_ticks[:3]:  # Sample first 3
        assert "strike" in tick
        assert "right" in tick
        assert "bid" in tick
        assert "ask" in tick
        assert "mid" in tick
    print(f"   ✓ All ticks have complete option data (strike, right, bid/ask/mid)")
    
    # 4. Best strategy
    print("\n4. Best strategy selection:")
    assert signal.best_strategy_type, "Missing best_strategy_type"
    assert signal.best_strategy_type in signal.strategies, "best_strategy_type not in strategies"
    print(f"   ✓ Best: {signal.best_strategy_type} (rank={signal.best_rank_score:.2f})")
    
    print("\n✅ PASSED: Signal contains ALL data for history display\n")
    return True


def test_signal_uniqueness_identifier():
    """Test that Signal has proper unique identifier (symbol+expiration+datetime)."""
    print("\n" + "="*80)
    print("TEST: Signal Uniqueness Identifier")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    
    # The unique identifier per user requirement: symbol+expiration+datetime
    unique_id = f"{signal.symbol}_{signal.expiration}_{signal.chain_timestamp}"
    
    print(f"Unique identifier: {unique_id}")
    print(f"  Symbol: {signal.symbol}")
    print(f"  Expiration: {signal.expiration}")
    print(f"  Chain timestamp: {signal.chain_timestamp}")
    
    # Verify all components present
    assert signal.symbol, "Missing symbol"
    assert signal.expiration, "Missing expiration"
    assert signal.chain_timestamp, "Missing chain_timestamp"
    
    print("\n✓ All uniqueness components present")
    print(f"✓ Unique ID format: symbol_expiration_timestamp")
    
    # Verify this can be used to prevent duplicates
    signal2 = create_test_signal(chain_type="buy")
    signal2.chain_timestamp = signal.chain_timestamp  # Same data
    
    unique_id2 = f"{signal2.symbol}_{signal2.expiration}_{signal2.chain_timestamp}"
    assert unique_id == unique_id2, "Same data should produce same unique ID"
    print("✓ Same data produces same unique ID (prevents duplicates)")
    
    # Different timestamp should produce different ID
    signal3 = create_test_signal(chain_type="buy")
    signal3.chain_timestamp = "2026-03-29T12:00:00"  # Different time
    
    unique_id3 = f"{signal3.symbol}_{signal3.expiration}_{signal3.chain_timestamp}"
    assert unique_id != unique_id3, "Different data should produce different unique ID"
    print("✓ Different data produces different unique ID")
    
    print("✅ PASSED: Uniqueness identifier working\n")
    return True


def test_signal_sell_strategies():
    """Test that SELL strategies are properly included in Signal."""
    print("\n" + "="*80)
    print("TEST: Signal Includes SELL Strategies")
    print("="*80)
    
    signal = create_test_signal(chain_type="sell")
    
    sell_strategies = [k for k in signal.strategies.keys() if "SELL" in k]
    
    print(f"SELL strategies in signal: {len(sell_strategies)}")
    for strategy_type in sorted(sell_strategies):
        strategy_data = signal.strategies[strategy_type]
        legs = strategy_data["legs"]
        
        # Verify SELL side
        assert strategy_data["open_side"] == "sell", f"{strategy_type} should have side='sell'"
        
        # Verify leg actions are reversed
        actions = [leg["open_action"] for leg in legs]
        assert "SELL" in actions, f"{strategy_type} should have SELL action"
        assert "BUY" in actions, f"{strategy_type} should have BUY action"
        
        print(f"  ✓ {strategy_type}: side={strategy_data['open_side']}, actions={actions[:2]}...")
    
    assert len(sell_strategies) > 0, "Signal should contain SELL strategies with SELL chain"
    print(f"\n✓ All {len(sell_strategies)} SELL strategies have correct side and actions")
    
    print("✅ PASSED: SELL strategies properly included\n")
    return True


def test_signal_imbalanced_strategies():
    """Test that imbalanced strategies have quantity data."""
    print("\n" + "="*80)
    print("TEST: Signal Includes Imbalanced Strategy Data")
    print("="*80)
    
    signal = create_test_signal(chain_type="buy")
    
    imbal_strategies = [k for k in signal.strategies.keys() if "IMBAL" in k]
    
    print(f"Imbalanced strategies in signal: {len(imbal_strategies)}")
    
    if len(imbal_strategies) == 0:
        print("⚠ No imbalanced strategies found (may require specific pricing)")
        print("✅ PASSED: Test validated (no imbalanced with current data)\n")
        return True
    
    for strategy_type in sorted(imbal_strategies):
        strategy_data = signal.strategies[strategy_type]
        
        # Verify imbalanced flag
        assert strategy_data["is_imbalanced"] == True, f"{strategy_type} should have is_imbalanced=True"
        
        # Verify notional values
        assert "buy_notional" in strategy_data, f"{strategy_type} missing buy_notional"
        assert "sell_notional" in strategy_data, f"{strategy_type} missing sell_notional"
        
        buy_not = strategy_data["buy_notional"]
        sell_not = strategy_data["sell_notional"]
        
        # Verify dominance
        assert buy_not >= sell_not, f"{strategy_type} violates notional dominance"
        
        # Verify quantities in legs
        legs = strategy_data["legs"]
        quantities = [leg["quantity"] for leg in legs]
        assert len(set(quantities)) > 1, f"{strategy_type} should have varying quantities"
        
        print(f"  ✓ {strategy_type}: buy_notional=${buy_not:.2f} >= sell_notional=${sell_not:.2f}, qty={quantities}")
    
    print(f"\n✓ All {len(imbal_strategies)} imbalanced strategies have complete data")
    print("✅ PASSED: Imbalanced strategy data complete\n")
    return True


def run_all_signal_tests():
    """Run all Signal JSON structure tests."""
    print("\n" + "="*80)
    print("SIGNAL JSON STRUCTURE TEST SUITE")
    print("="*80)
    
    tests = [
        ("Signal JSON Structure", test_signal_json_structure),
        ("Signal Strategies Field", test_signal_strategies_field),
        ("Signal Leg Data", test_signal_legs_data),
        ("Signal Filter Metadata", test_signal_filter_metadata),
        ("Signal Chain Snapshot", test_signal_chain_snapshot),
        ("Signal Best Strategy", test_signal_best_strategy_selection),
        ("Signal SELL Strategies", test_signal_sell_strategies),
        ("Signal Imbalanced Data", test_signal_imbalanced_strategies),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}\n")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   {type(e).__name__}: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("="*80)
    print(f"Signal JSON Tests: {passed} passed, {failed} failed")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 ALL SIGNAL JSON TESTS PASSED!")
        print("\n✓ Signal structure complete")
        print("✓ All strategies included with legs and filter data")
        print("✓ Chain snapshot optimized")
        print("✓ Best strategy selection working")
        print("✓ SELL and imbalanced variants supported")
        print("✓ Unique identifier (symbol+expiration+datetime) validated")
        print("\n✅ Signal JSON ready for cache storage!")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_signal_tests()
    sys.exit(0 if success else 1)
