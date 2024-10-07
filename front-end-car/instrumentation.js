/*instrumentation.js*/
// // Require dependencies
// const { NodeSDK } = require('@opentelemetry/sdk-node');
// const { ConsoleSpanExporter } = require('@opentelemetry/sdk-trace-node');
// const {
//   getNodeAutoInstrumentations,
// } = require('@opentelemetry/auto-instrumentations-node');
// const {
//   PeriodicExportingMetricReader,
//   ConsoleMetricExporter,
// } = require('@opentelemetry/sdk-metrics');
// const { Resource } = require('@opentelemetry/resources')


// const sdk = new NodeSDK({
//   // traceExporter: new ConsoleSpanExporter(),
//   metricReader: new PeriodicExportingMetricReader({
//     exporter: new ConsoleMetricExporter(),
//   }),
//   instrumentations: [getNodeAutoInstrumentations()],
//   resource: new Resource({
//     'service.name': 'front-end-car',
//     'service.version': '1.0.0',
//   }),
// });

// sdk.start();

const { NodeSDK } = require('@opentelemetry/sdk-node');
const {
  OTLPTraceExporter,
} = require('@opentelemetry/exporter-trace-otlp-proto');
const {
  OTLPMetricExporter,
} = require('@opentelemetry/exporter-metrics-otlp-proto');
const {
  getNodeAutoInstrumentations,
} = require('@opentelemetry/auto-instrumentations-node');
const {
  PeriodicExportingMetricReader,
} = require('@opentelemetry/sdk-metrics');
const { Resource } = require('@opentelemetry/resources');

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: 'http://localhost:4242/v1/traces',
    // optional - collection of custom headers to be sent with each request, empty by default
    headers: {},
  }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: 'http://localhost:4242/v1/metrics',
      headers: {}, // an optional object containing custom headers to be sent with each request
      concurrencyLimit: 1, // an optional limit on pending requests
    }),
  }),
  instrumentations: [getNodeAutoInstrumentations()],
  resource: new Resource({
    'service.name': 'front-end-car',
    'service.version': '1.0.0',
  }),
});

sdk.start();
