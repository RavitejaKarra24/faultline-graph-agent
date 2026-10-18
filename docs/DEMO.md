# Faultline demo

[Watch the 2:30 walkthrough on YouTube](https://youtu.be/TjTtA-2QQ_w).

The recording shows the running application with AI summary synthesis enabled. The company data is fictional, the graph queries are real, and approvals are simulated. Narration uses an AI-generated stock voice.

## In the video

| Time | Feature |
| --- | --- |
| 0:00 | Start with a Redis timeout |
| 0:10 | Investigate affected services, customers, and owners |
| 0:28 | Follow the customer-to-service dependency chain |
| 0:42 | Inspect the seven executed graph stages and exact Cypher |
| 1:00 | Save an avoid lesson in workspace memory |
| 1:20 | Start a new session and recall the saved lesson |
| 1:32 | See the lesson change runbook proposals into review tasks |
| 1:42 | Record a simulated approval |
| 1:50 | Disable Payments API → Redis and re-investigate |
| 2:08 | See the impact shrink to Analytics and Orbit Labs |
| 2:20 | Inspect the exact remaining evidence path |

## Try it locally

Start the app using the [README setup instructions](../README.md#run-it--no-ai-key-required).

1. With Payments API → Redis enabled, investigate Redis. The fixture returns six downstream services and three customers.
2. Open an evidence path and expand a query in the trace. Inspect its Cypher, parameters, result count, and duration.
3. In **Memory**, save an avoid lesson: “Avoid blanket Redis restarts during checkout traffic. Drain payment connection pools first.”
4. Start a **New session** and investigate again. The lesson is recalled, and applicable runbook proposals require review.
5. Disable **Payments API → Redis** and re-investigate. Analytics and Orbit Labs remain in the Redis blast radius; the payment branch drops out.
6. Re-enable the dependency after comparing the results.

Approving a task persists an approval record. It does not send a notification or execute a runbook. Graph traversal and task planning work without an AI key; optional model synthesis changes the summary wording.
