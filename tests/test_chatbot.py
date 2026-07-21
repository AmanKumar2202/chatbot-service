import unittest

from app.services.ai_engine import generate_reply, generate_smart_replies


class ChatbotTests(unittest.TestCase):
    def test_greeting(self):
        reply, intent, confidence = generate_reply("hello")
        self.assertEqual(intent, "greeting")
        self.assertGreater(confidence, 0)
        self.assertTrue(reply)

    def test_paragraph(self):
        reply, intent, _ = generate_reply("write a paragraph about technology")
        self.assertEqual(intent, "paragraph")
        self.assertIn("Technology", reply)

    def test_smart_replies(self):
        replies, intent = generate_smart_replies("hello", 3)
        self.assertEqual(intent, "greeting")
        self.assertEqual(len(replies), 3)

    def test_humanized_formal_message(self):
        reply, intent, _ = generate_reply("Write a humanized formal email to my manager about two days of leave")
        self.assertEqual(intent, "formal")
        self.assertIn("Dear Manager", reply)
        self.assertIn("two days of leave", reply.lower())

    def test_long_text_summary(self):
        text = "Artificial intelligence helps teams automate repetitive work. It can analyze large datasets quickly. Developers use it to improve software quality. Responsible AI also requires privacy and human oversight. Good governance reduces risk and builds trust."
        reply, intent, _ = generate_reply(f"Summarize this: {text}")
        self.assertEqual(intent, "summarize")
        self.assertLess(len(reply), len(text))

    def test_busy_weekend_reply(self):
        reply, intent, _ = generate_reply("Write a short reply telling them I am busy today but available this weekend.")
        self.assertEqual(intent, "reply")
        self.assertEqual(reply, "I'm busy today but available this weekend.")

    def test_friendly_dinner_reply(self):
        reply, intent, _ = generate_reply("Generate a friendly and natural reply confirming that I am available for dinner tomorrow evening.")
        self.assertEqual(intent, "reply")
        self.assertIn("available for dinner tomorrow evening", reply)

    def test_tone_without_content_asks_for_detail(self):
        reply, intent, _ = generate_reply("Write a reply that sounds friendly, confident, and natural. Keep it under two sentences.")
        self.assertEqual(intent, "reply")
        self.assertIn("What should the reply say?", reply)

    def test_project_update_smart_replies(self):
        message = "Subject: Project update. The chatbot integration is complete, review is pending, and the code has been pushed to GitHub. Thank you for your time."
        replies, _ = generate_smart_replies(message, 3)
        self.assertIn("review", replies[0].lower())
        self.assertNotIn("welcome", " ".join(replies).lower())

    def test_short_thanks_smart_replies(self):
        replies, _ = generate_smart_replies("Thank you for your help!", 3)
        self.assertEqual(replies[0], "You're welcome!")


if __name__ == "__main__":
    unittest.main()
