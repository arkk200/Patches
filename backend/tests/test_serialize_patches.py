from app.schemas.puzzle import PatchDefinition, PuzzleDraft
from app.services.parse_patches import parse_patches
from app.services.serialize_patches import serialize_patches


SAMPLE_1 = """\
5x5
..a..
.....
b.c.d
.....
..e..
a:5:wide
b:8:tall
c:2:tall
d:4:square
e:6:wide"""

SAMPLE_3 = """\
6x6
.a..b.
..c...
.....d
e.....
...f..
.g..h.
a:4:tall
b:4:square
c:4:square
d:-:wide
e:-:tall
f:4:wide
g:4:wide
h:4:square"""


class TestSerializePatches:
    def test_round_trip_sample_1(self) -> None:
        draft = parse_patches(SAMPLE_1)
        result = serialize_patches(draft)
        assert result == SAMPLE_1

    def test_round_trip_sample_3(self) -> None:
        draft = parse_patches(SAMPLE_3)
        result = serialize_patches(draft)
        assert result == SAMPLE_3

    def test_sorts_patches_by_id(self) -> None:
        draft = PuzzleDraft(
            width=5,
            height=5,
            board_rows=["ab...", ".....", ".....", ".....", "....."],
            patches=[
                PatchDefinition(id="b", row=0, col=1, size=3, shape="wide"),
                PatchDefinition(id="a", row=0, col=0, size=5, shape="tall"),
            ],
        )
        result = serialize_patches(draft)
        expected = """\
5x5
ab...
.....
.....
.....
.....
a:5:tall
b:3:wide"""
        assert result == expected
