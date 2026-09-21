from engine.sequence import (
    Contact, FaceMediumCell, FaceSoluteCell, SequenceSiteLocation,
    SequenceState, SpatialSequenceState, Strand, observe_face_compartments,
)


def _boundary(divided: bool, closed: bool = True) -> SpatialSequenceState:
    strand = Strand(1, (1, 0, 1, 2, 3, 2), cyclic=closed)
    contact = (Contact(1, 1, 1, 4, 1, 2),) if divided else ()
    return SpatialSequenceState(
        SequenceState((strand,), thermal_energy=10, contacts=contact), 3, 2,
        (
            SequenceSiteLocation(1, 0, 0, 0), SequenceSiteLocation(1, 1, 1, 0),
            SequenceSiteLocation(1, 2, 2, 0), SequenceSiteLocation(1, 3, 2, 1),
            SequenceSiteLocation(1, 4, 1, 1), SequenceSiteLocation(1, 5, 0, 1),
        ),
    )


def test_physical_partition_splits_local_contents_without_copying_or_assignment():
    medium = (FaceMediumCell(0, 0, 4, 1), FaceMediumCell(1, 0, 6, 2))
    solutes = (FaceSoluteCell(0, 0, 0, 3), FaceSoluteCell(1, 0, 0, 7))
    parent = observe_face_compartments(_boundary(False), medium)
    children = observe_face_compartments(_boundary(True), medium)

    assert len(parent) == 1 and parent[0].interior_faces == ((0, 0), (1, 0))
    assert len(children) == 2
    solute_at = {(cell.face, cell.kind): cell.amount for cell in solutes}
    inherited = sorted(
        sum(solute_at.get((face, 0), 0) for face in child.interior_faces)
        for child in children
    )
    assert inherited == [3, 7]
    assert sum(inherited) == 10


def test_partition_removal_fuses_volumes_and_boundary_opening_removes_compartment():
    medium = (FaceMediumCell(0, 0, 4, 1), FaceMediumCell(1, 0, 6, 2))
    assert len(observe_face_compartments(_boundary(True), medium)) == 2
    assert len(observe_face_compartments(_boundary(False), medium)) == 1
    assert observe_face_compartments(_boundary(False, closed=False), medium) == ()
