"""Contract checks for the FastAPI service when no hosted database is configured."""
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError
from main import EventInput, create_event, health, products

class ApiContractTests(unittest.TestCase):
    def without_database(self, handler, *args):
        with patch.dict("os.environ", {"DATABASE_URL":""}):
            with self.assertRaises(HTTPException) as caught:
                handler(*args)
        return caught.exception

    def test_health_reports_unavailable_database(self):
        error = self.without_database(health)
        self.assertEqual(error.status_code, 503)
        self.assertIn("DATABASE_URL", error.detail)

    def test_health_explains_unreplaced_connection_placeholder(self):
        with patch.dict("os.environ", {"DATABASE_URL":"YOUR_SUPABASE_POSTGRESQL_CONNECTION_STRING"}):
            with self.assertRaises(HTTPException) as caught:
                health()
        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("placeholder", caught.exception.detail)

    def test_catalog_does_not_return_fake_products(self):
        error = self.without_database(products)
        self.assertEqual(error.status_code, 503)

    def test_event_is_not_reported_as_persisted_without_database(self):
        event = EventInput(**{
            "session_id":"session-12345678", "customer_id":"customer-12345678",
            "device_type":"Desktop", "action":"View Product", "product_id":"linen-shirt"
        })
        error = self.without_database(create_event, event)
        self.assertEqual(error.status_code, 503)

    def test_action_payload_rejects_unknown_symbols(self):
        with self.assertRaises(ValidationError):
            EventInput(**{
            "session_id":"session-12345678", "customer_id":"customer-12345678",
            "device_type":"Desktop", "action":"Pay Now"
        })

    def test_products_returns_rows_from_database_query(self):
        conn = MagicMock()
        expected = [{"id":"arc-ceramic-vase", "name":"Arc Ceramic Vase", "category":"Home Decor",
                     "description":"A vase.", "price":2890.0, "image_url":"https://example.test/vase.jpg", "featured":True}]
        conn.execute.return_value.fetchall.return_value = expected
        @contextmanager
        def fake_database():
            yield conn
        with patch("main.database", fake_database):
            self.assertEqual(products(), expected)
        sql = conn.execute.call_args.args[0]
        self.assertIn("FROM products", sql)
        self.assertIn("price::float AS price", sql)

    def test_event_creates_session_and_inserts_persistable_event(self):
        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = {
            "id": 41, "action":"Add to Cart", "product_id":"arc-ceramic-vase",
            "quantity":1, "created_at":"2026-10-29T00:00:00Z"
        }
        @contextmanager
        def fake_database():
            yield conn
        event = EventInput(session_id="session-12345678", customer_id="customer-12345678",
                           device_type="Desktop", action="Add to Cart", product_id="arc-ceramic-vase")
        with patch("main.database", fake_database):
            result = create_event(event)
        self.assertEqual(result["id"], 41)
        statements = [call.args[0] for call in conn.execute.call_args_list]
        self.assertTrue(any("INSERT INTO shopping_sessions" in sql for sql in statements))
        self.assertTrue(any("INSERT INTO session_events" in sql for sql in statements))

if __name__ == "__main__":
    unittest.main()
