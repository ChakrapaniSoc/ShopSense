import unittest
import pandas as pd
from modules.automata import process_actions
from modules.analytics import calculate_metrics

class AutomataTests(unittest.TestCase):
    def test_successful_purchase(self): self.assertEqual(process_actions(["View Product","Add to Cart","Checkout","Purchase"]).status,"completed")
    def test_valid_abandonment(self): self.assertEqual(process_actions(["View Product","Add to Cart","Abandon"]).status,"abandoned")
    def test_browse_only_is_incomplete(self): self.assertEqual(process_actions(["Browse","View Product"]).status,"incomplete")
    def test_repeated_views(self): self.assertEqual(process_actions(["View Product","View Product"]).final_state,"S1")
    def test_remove_item(self): self.assertEqual(process_actions(["View Product","Add to Cart","Remove from Cart"]).final_state,"S1")
    def test_invalid_action_order(self): self.assertEqual(process_actions(["Purchase"]).status,"invalid")
    def test_empty_is_incomplete(self): self.assertEqual(process_actions([]).status,"incomplete")
    def test_transition_explanations(self): self.assertIn("checkout",process_actions(["View Product","Add to Cart","Checkout"]).transitions[-1]["explanation"].lower())

class AnalyticsTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([{"session_id":"1","customer_id":"a","timestamp":"2025-01-01","device_type":"Mobile","product_category":"Books","actions":"[]","items_viewed":1,"items_added_to_cart":1,"checkout_started":False,"purchase_completed":False,"session_duration_seconds":60,"total_purchase_amount":0},{"session_id":"2","customer_id":"b","timestamp":"2025-01-02","device_type":"Desktop","product_category":"Books","actions":"[]","items_viewed":1,"items_added_to_cart":1,"checkout_started":True,"purchase_completed":True,"session_duration_seconds":120,"total_purchase_amount":100}])
    def test_rates(self):
        m=calculate_metrics(self.frame());self.assertEqual(m["conversion_rate"],50);self.assertEqual(m["cart_abandonment_rate"],50);self.assertEqual(m["checkout_abandonment_rate"],0)
    def test_empty_frame_with_schema(self):
        m=calculate_metrics(self.frame().iloc[0:0]);self.assertEqual(m["total_sessions"],0);self.assertEqual(m["conversion_rate"],0)
    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError): calculate_metrics(pd.DataFrame({"session_id":[]}))
    def test_invalid_numeric_values_safe(self):
        frame=self.frame().astype({"session_duration_seconds":"object"});frame.loc[0,"session_duration_seconds"]="bad";self.assertGreaterEqual(calculate_metrics(frame)["average_session_duration"],0)

if __name__ == "__main__": unittest.main()
