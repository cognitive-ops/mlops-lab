import winston from 'winston';

const logLevel = process.env.LOG_LEVEL || 'info';

// Safe stringifier that handles circular references
const safeStringify = (obj: any): string => {
  const seen = new WeakSet();
  return JSON.stringify(obj, (key, value) => {
    if (typeof value === 'object' && value !== null) {
      if (seen.has(value)) {
        return '[Circular]';
      }
      seen.add(value);
    }
    // Skip certain properties to avoid verbose output
    if (key === 'service' || key === 'stack') {
      return undefined;
    }
    return value;
  }, 2);
};

export const logger = winston.createLogger({
  level: logLevel,
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.splat(),
    winston.format.json(),
    winston.format.printf(({ timestamp, level, message, ...rest }) => {
      let metaStr = '';
      if (Object.keys(rest).length > 0) {
        try {
          metaStr = ' ' + safeStringify(rest);
        } catch (e) {
          metaStr = ' [Unable to serialize metadata]';
        }
      }
      return `${timestamp} [${level.toUpperCase()}]: ${message}${metaStr}`;
    })
  ),
  defaultMeta: { service: 'codepipeline-metrics-api' },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ timestamp, level, message, ...rest }) => {
          let metaStr = '';
          if (Object.keys(rest).length > 0) {
            try {
              metaStr = ' ' + safeStringify(rest);
            } catch (e) {
              metaStr = ' [Unable to serialize metadata]';
            }
          }
          return `${timestamp} [${level}]: ${message}${metaStr}`;
        })
      ),
    }),
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
  ],
});
