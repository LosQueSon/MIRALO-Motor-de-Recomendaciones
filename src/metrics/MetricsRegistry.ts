interface EndpointMetrics {
  requestCount: number;
  totalLatencyMs: number;
  errorCount: number;
}

export interface MetricsSnapshot {
  endpoints: Record<
    string,
    {
      request_count: number;
      average_latency_ms: number;
      error_rate: number;
    }
  >;
  recommendations_generated: number;
  score_distribution: Record<string, number>;
}

export class MetricsRegistry {
  private readonly endpointMetrics = new Map<string, EndpointMetrics>();
  private recommendationsGenerated = 0;
  private readonly scoreDistribution = new Map<string, number>([
    ["0.0-0.2", 0],
    ["0.2-0.4", 0],
    ["0.4-0.6", 0],
    ["0.6-0.8", 0],
    ["0.8-1.0", 0]
  ]);

  trackRequest(endpoint: string, statusCode: number, latencyMs: number): void {
    const current = this.endpointMetrics.get(endpoint) ?? {
      requestCount: 0,
      totalLatencyMs: 0,
      errorCount: 0
    };

    current.requestCount += 1;
    current.totalLatencyMs += latencyMs;
    if (statusCode >= 500) {
      current.errorCount += 1;
    }

    this.endpointMetrics.set(endpoint, current);
  }

  trackRecommendations(scores: number[]): void {
    this.recommendationsGenerated += scores.length;
    for (const score of scores) {
      const bucket = this.getBucket(score);
      this.scoreDistribution.set(bucket, (this.scoreDistribution.get(bucket) ?? 0) + 1);
    }
  }

  snapshot(): MetricsSnapshot {
    const endpoints: MetricsSnapshot["endpoints"] = {};

    for (const [endpoint, data] of this.endpointMetrics.entries()) {
      endpoints[endpoint] = {
        request_count: data.requestCount,
        average_latency_ms:
          data.requestCount > 0
            ? Number((data.totalLatencyMs / data.requestCount).toFixed(2))
            : 0,
        error_rate:
          data.requestCount > 0
            ? Number((data.errorCount / data.requestCount).toFixed(4))
            : 0
      };
    }

    return {
      endpoints,
      recommendations_generated: this.recommendationsGenerated,
      score_distribution: Object.fromEntries(this.scoreDistribution.entries())
    };
  }

  private getBucket(score: number): string {
    if (score < 0.2) return "0.0-0.2";
    if (score < 0.4) return "0.2-0.4";
    if (score < 0.6) return "0.4-0.6";
    if (score < 0.8) return "0.6-0.8";
    return "0.8-1.0";
  }
}

