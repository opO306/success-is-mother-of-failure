import sys
import pytest
from experiments.verified_superoptimizer_c1b1 import pilot3_allocations as A

@pytest.fixture(scope='module')
def probe(tmp_path_factory):
    return A.build(tmp_path_factory.mktemp('pilot3_alloc_parent')/'native')

def test_real_heap_integer_count_and_bytes(probe):
    value=1<<130
    row=A.measure(probe,lambda:value+1,31)
    assert row['bigint_objects']==31 and row['heap_integer_objects']==31
    assert row['bigint_max_bits']==131
    # CPython addition reserves a carry limb even when normalization removes it.
    assert row['bigint_max_object_bytes']==sys.getsizeof(value+1)+4
    assert row['bigint_peak_live_bytes']==row['bigint_max_object_bytes']
    assert row['bigint_allocated_bytes']==31*row['bigint_max_object_bytes']

def test_cached_integer_is_not_falsely_counted(probe):
    assert A.measure(probe,lambda:1,31)['heap_integer_objects']==0

def test_allocator_restored_after_original_exception(probe):
    def fail():raise ValueError('original refusal')
    with pytest.raises(ValueError,match='original refusal'):A.measure(probe,fail,1)
    value=1<<130
    assert A.measure(probe,lambda:value+1,7)['bigint_objects']==7

def test_executed_raw_integer_multiply_count():
    from a_reference import c1b1_pilot3_impulse as X
    value,ops=A.operations(lambda:X.component_interval((100,101),3,48,__import__('fractions').Fraction(20),128))
    assert ops['integer *']==4
    assert value==(6000,6060,1<<176)
