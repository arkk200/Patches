import pydantic
import pytest

from app.schemas.puzzle import PuzzleDraft
from app.services.parse_patches import parse_patches


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

SAMPLE_2 = """\
5x5
a...b
.....
..c..
.....
d...e
a:3:wide
b:4:none
c:8:none
d:4:none
e:6:tall"""

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


class TestParsePatches:
    def test_sample_1(self) -> None:
        result = parse_patches(SAMPLE_1)

        assert isinstance(result, PuzzleDraft)
        assert result.width == 5
        assert result.height == 5
        assert result.board_rows == [
            "..a..",
            ".....",
            "b.c.d",
            ".....",
            "..e..",
        ]
        assert len(result.patches) == 5

        patch_a = result.patches[0]
        assert patch_a.id == "a"
        assert patch_a.row == 0
        assert patch_a.col == 2
        assert patch_a.size == 5
        assert patch_a.shape == "wide"

    def test_sample_2_positions(self) -> None:
        result = parse_patches(SAMPLE_2)

        assert result.width == 5
        assert result.height == 5
        assert result.board_rows == [
            "a...b",
            ".....",
            "..c..",
            ".....",
            "d...e",
        ]

        by_id = {p.id: p for p in result.patches}
        assert by_id["a"].row == 0 and by_id["a"].col == 0
        assert by_id["b"].row == 0 and by_id["b"].col == 4
        assert by_id["c"].row == 2 and by_id["c"].col == 2
        assert by_id["d"].row == 4 and by_id["d"].col == 0
        assert by_id["e"].row == 4 and by_id["e"].col == 4

    def test_sample_3_unknown_sizes(self) -> None:
        result = parse_patches(SAMPLE_3)

        assert result.width == 6
        assert result.height == 6

        by_id = {p.id: p for p in result.patches}
        assert by_id["d"].size is None
        assert by_id["e"].size is None
        assert by_id["a"].size == 4
        assert by_id["h"].size == 4

    def test_strips_extra_whitespace(self) -> None:
        content = "  5x2  \n  ..a..  \n  .....  \n  a:3:wide  "
        result = parse_patches(content)

        assert result.width == 5
        assert result.height == 2
        assert result.board_rows == [
            "..a..",
            ".....",
        ]
        assert result.patches[0].id == "a"
        assert result.patches[0].size == 3

    def test_skips_empty_lines(self) -> None:
        content = "5x2\n\n..a..\n\n.....\na:3:wide\n"
        result = parse_patches(content)

        assert result.width == 5
        assert result.height == 2
        assert result.board_rows == [
            "..a..",
            ".....",
        ]
        assert len(result.patches) == 1

    def test_empty_content_raises(self) -> None:
        with pytest.raises(IndexError):
            parse_patches("")

    def test_malformed_size_line_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_patches("invalid\na\nb")

    def test_patch_id_not_in_board_raises(self) -> None:
        content = """\
3x3
...
...
...
x:5:wide"""
        with pytest.raises(KeyError):
            parse_patches(content)

    def test_zero_size_raises_validation_error(self) -> None:
        content = """\
3x3
a..
...
...
a:0:wide"""
        with pytest.raises(pydantic.ValidationError):
            parse_patches(content)
