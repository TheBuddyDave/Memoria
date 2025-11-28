/**
 * Cloudflare Pages Function for waitlist signups
 * Handles POST requests to /api/waitlist
 * 
 * Requires D1 database binding named "DB" in wrangler.toml
 */

export async function onRequestPost(context) {
  const { request, env } = context;

  try {
    // Parse request body
    const body = await request.json();
    const { email } = body;

    // Validate email
    if (!email || typeof email !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Email is required' }),
        { 
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return new Response(
        JSON.stringify({ error: 'Invalid email format' }),
        { 
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // Normalize email (lowercase, trim)
    const normalizedEmail = email.toLowerCase().trim();

    // Check if email already exists
    const existing = await env.DB.prepare(
      'SELECT id FROM waitlist WHERE email = ?'
    ).bind(normalizedEmail).first();

    if (existing) {
      return new Response(
        JSON.stringify({ 
          success: true, 
          message: 'You\'re already on the waitlist!',
          alreadyExists: true
        }),
        { 
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // Insert into database
    const timestamp = new Date().toISOString();
    await env.DB.prepare(
      'INSERT INTO waitlist (email, created_at) VALUES (?, ?)'
    ).bind(normalizedEmail, timestamp).run();

    return new Response(
      JSON.stringify({ 
        success: true, 
        message: 'Successfully added to waitlist!'
      }),
      { 
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );

  } catch (error) {
    console.error('Waitlist error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to process request' }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

// Handle OPTIONS for CORS preflight
export async function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

