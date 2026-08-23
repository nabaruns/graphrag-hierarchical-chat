import type { IngestDoc } from "./api";

// The bundled demo corpus. Ingest these, then ask the example questions below.
export const SAMPLE_DOCS: IngestDoc[] = [
  {
    title: "TechCorp Acquisition News",
    source: "sample/news-1",
    text: "TechCorp announced today that it has acquired DataStart, an AI analytics startup founded in 2019 by Dr. Elena Reyes. DataStart is based in Austin, Texas, and is known for its real-time streaming analytics platform called StreamIQ. The acquisition, valued at 450 million dollars, is expected to strengthen TechCorp's cloud division. Dr. Elena Reyes will join TechCorp as the Vice President of AI Engineering, reporting directly to TechCorp CEO Marcus Chen. Marcus Chen said the deal reflects TechCorp's long-term strategy to invest in real-time data infrastructure. TechCorp is headquartered in Seattle and previously acquired CloudNimbus in 2021.",
  },
  {
    title: "StreamIQ Product Overview",
    source: "sample/product-1",
    text: "StreamIQ is a real-time streaming analytics platform originally developed by DataStart. It is built on top of Apache Kafka and uses a custom query engine written in Rust. StreamIQ integrates with major cloud providers and supports anomaly detection powered by machine learning models. After the acquisition by TechCorp, StreamIQ was integrated into the TechCorp Cloud Suite. The engineering team behind StreamIQ is led by Priya Nair, who worked closely with Dr. Elena Reyes at DataStart. StreamIQ competes with products from CloudNimbus, which is now also part of TechCorp.",
  },
  {
    title: "TechCorp Leadership",
    source: "sample/company-1",
    text: "Marcus Chen co-founded TechCorp in 2010 along with Sarah Whitfield. Sarah Whitfield currently serves as the Chief Technology Officer of TechCorp. Under their leadership, TechCorp grew from a small Seattle startup into a major cloud computing company. Marcus Chen previously worked at CloudNimbus before founding TechCorp. Sarah Whitfield holds several patents in distributed systems and mentors the AI Engineering group now led by Dr. Elena Reyes.",
  },
];

// Questions tuned to the sample corpus. The multi-hop ones require stitching
// facts across documents via the knowledge graph.
export const EXAMPLE_PROMPTS: { q: string; hint?: string }[] = [
  { q: "Who acquired DataStart, and who founded it?" },
  { q: "What is StreamIQ built on, and which company owns it now?" },
  { q: "How is Dr. Elena Reyes connected to Marcus Chen?", hint: "multi-hop" },
  { q: "Which companies has TechCorp acquired?" },
  { q: "Who co-founded TechCorp and what are their roles?" },
];
