from elevator_sim.traffic.grid import GridSpace


def test_grid_indices_within_bounds():
    grid = GridSpace(width_m=20.0, height_m=20.0, nx=50, ny=50)
    xi, yi = grid.to_grid_indices(0.0, 0.0)
    assert (xi, yi) == (0, 0)

    xi, yi = grid.to_grid_indices(19.99, 19.99)
    assert xi == 49 and yi == 49


def test_grid_indices_clamped_outside_bounds():
    grid = GridSpace(width_m=20.0, height_m=20.0, nx=50, ny=50)
    xi, yi = grid.to_grid_indices(-5.0, 100.0)
    assert xi == 0
    assert yi == 49


def test_grid_id_formula_matches_paper():
    grid = GridSpace(width_m=20.0, height_m=20.0, nx=50, ny=50)
    # p* = y* * Nx + x*
    assert grid.grid_id(xi=3, yi=2) == 2 * 50 + 3
    assert grid.num_cells == 50 * 50
