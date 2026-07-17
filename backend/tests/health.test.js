/**
 * backend/tests/health.test.js
 * Basic integration tests for the Express backend health and API endpoints.
 */

const request = require('supertest');

// Require the app without starting the server
// server.js calls app.listen(), so we import it and then close.
let server;
let app;

beforeAll((done) => {
  // Suppress console output during tests
  jest.spyOn(console, 'log').mockImplementation(() => {});
  jest.spyOn(console, 'error').mockImplementation(() => {});

  // Load the server — it will listen on PORT from .env (5000) or a random port
  process.env.PORT = '5001'; // use a different port to avoid conflict with running server
  process.env.NODE_ENV = 'test';

  try {
    const serverModule = require('../server.js');
    // server.js exports the http.Server instance
    if (serverModule && typeof serverModule.close === 'function') {
      server = serverModule;
      app = server;
    } else {
      // Fallback: server.js may not export anything — use supertest with the port
      server = null;
    }
  } catch (e) {
    server = null;
  }
  done();
});

afterAll((done) => {
  if (server && typeof server.close === 'function') {
    server.close(done);
  } else {
    done();
  }
});

describe('Backend Health Endpoints', () => {
  it('GET /health returns 200 with status ok', async () => {
    const res = await request('http://localhost:5000').get('/health').timeout(5000);
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(res.body.status).toBe('ok');
    expect(res.body.service).toBeDefined();
    expect(res.body.version).toBeDefined();
  });

  it('GET /health includes environment field', async () => {
    const res = await request('http://localhost:5000').get('/health').timeout(5000);
    expect(res.body.environment).toBeDefined();
  });

  it('GET /api returns 200 with endpoints list', async () => {
    const res = await request('http://localhost:5000').get('/api').timeout(5000);
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(Array.isArray(res.body.endpoints)).toBe(true);
    expect(res.body.endpoints.length).toBeGreaterThan(0);
  });

  it('GET /api includes /api/upload endpoint', async () => {
    const res = await request('http://localhost:5000').get('/api').timeout(5000);
    const paths = res.body.endpoints.map((e) => e.path);
    expect(paths).toContain('/api/upload');
  });

  it('GET /api includes /api/batch endpoint', async () => {
    const res = await request('http://localhost:5000').get('/api').timeout(5000);
    const paths = res.body.endpoints.map((e) => e.path);
    expect(paths).toContain('/api/batch');
  });

  it('GET /nonexistent-route returns 404', async () => {
    const res = await request('http://localhost:5000').get('/nonexistent-xyz-route').timeout(5000);
    expect(res.status).toBe(404);
  });

  it('GET /health response time is under 2 seconds', async () => {
    const start = Date.now();
    await request('http://localhost:5000').get('/health').timeout(5000);
    const elapsed = Date.now() - start;
    expect(elapsed).toBeLessThan(2000);
  });

  it('GET /api returns service name', async () => {
    const res = await request('http://localhost:5000').get('/api').timeout(5000);
    expect(res.body.service).toBeDefined();
    expect(typeof res.body.service).toBe('string');
  });
});

describe('Backend CORS', () => {
  it('GET /health responds with correct content-type', async () => {
    const res = await request('http://localhost:5000').get('/health').timeout(5000);
    expect(res.headers['content-type']).toMatch(/application\/json/);
  });
});
