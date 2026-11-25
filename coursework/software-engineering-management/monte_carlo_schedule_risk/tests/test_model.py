import unittest

from config import DATA_PATH
from schedule_model import (
    deterministic_schedule,
    load_tasks,
    sample_task_durations,
    simulate_project,
    validate_tasks,
)


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = load_tasks(DATA_PATH)

    def test_graph_is_valid(self):
        validate_tasks(self.tasks)

    def test_beta_mean_matches_pert(self):
        samples = sample_task_durations(self.tasks, 200_000, seed=7)
        for idx, task in enumerate(self.tasks):
            self.assertAlmostEqual(
                samples[:, idx].mean(),
                task.pert_mean,
                delta=0.12,
                msg=f"mean mismatch for {task.task_id}",
            )

    def test_deterministic_duration_is_positive(self):
        schedule = deterministic_schedule(self.tasks)
        self.assertGreater(schedule["project_duration"], 0)
        self.assertTrue(schedule["critical_ids"])

    def test_simulation_has_expected_size(self):
        simulation = simulate_project(self.tasks, 500, seed=10)
        self.assertEqual(simulation["project_duration"].shape, (500,))


if __name__ == "__main__":
    unittest.main()
