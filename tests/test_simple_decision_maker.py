import unittest

from Backend.SimpleDecisionMaker import SimplePatternMatcher


class SimpleDecisionMakerTests(unittest.TestCase):
    def setUp(self):
        self.matcher = SimplePatternMatcher()

    def test_youtube_control_routes_without_cohere(self):
        cases = {
            "pause the video": ["youtube control pause"],
            "pause youtube": ["youtube control pause"],
            "resume the video": ["youtube control resume"],
            "play": ["youtube control resume"],
            "unpause": ["youtube control resume"],
            "make it fullscreen": ["youtube control fullscreen"],
            "turn on captions": ["youtube control captions"],
            "set speed to 1.5": ["youtube control speed 1.5"],
            "skip forward 10 seconds": ["youtube control skip forward 10"],
            "cancel the timer": ["youtube control cancel timer"],
            "youtube volume 70": ["youtube control volume 70"],
            "mute the video": ["youtube control mute"],
            "close youtube": ["youtube control close youtube"],
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.matcher.decide(query), expected)

    def test_non_youtube_commands_are_not_stolen(self):
        cases = {
            "open chrome": ["open chrome"],
            "play lo-fi music": ["play lo-fi music"],
            "mute my laptop": ["system mute"],
            "what is the weather today": ["realtime what is the weather today"],
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.matcher.decide(query), expected)

    def test_reminder_route(self):
        self.assertEqual(
            self.matcher.decide("remind me in 10 minutes to stretch"),
            ["reminder in 10 minutes to stretch"],
        )

    def test_reminder_action_routes(self):
        cases = {
            "show my reminders": ["reminder show my reminders"],
            "cancel my medicine reminder": ["reminder cancel my medicine reminder"],
            "snooze this for 10 minutes": ["reminder snooze this for 10 minutes"],
        }

        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.matcher.decide(query), expected)


if __name__ == "__main__":
    unittest.main()
