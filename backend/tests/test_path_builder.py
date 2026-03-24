from app.services.path_builder import (
    build_candidate_patches_path,
    build_final_patches_path,
)


def test_build_candidate_patches_path():
    path = build_candidate_patches_path(22, 1)
    assert path.endswith("22-1.patches")


def test_build_final_patches_path():
    path = build_final_patches_path(22)
    assert path.endswith("22.patches")
