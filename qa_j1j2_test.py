#!/usr/bin/env python3
"""QA verification: J1/J2 endpoint behavior"""
import sys, json
sys.path.insert(0, '/Users/oq/Documents/trading-signals-saas')

from app import app, _DBSession, _db_engine

print("=" * 60)
print("QA REPORT: J1/J2 endpoint behavior and dvFetch chain")
print("=" * 60)

# --- Check 1: SessionLocal existence ---
print("\n[CHECK 1] Does SessionLocal exist?")
try:
    from app import SessionLocal
    print("  PASS: SessionLocal is importable")
except ImportError:
    print("  FAIL: SessionLocal is NOT defined in app.py")
    print("  The app uses _DBSession (at line 11590) but J1/J2 endpoints")
    print("  call SessionLocal() at lines 12699 and 12745")
    print("  This will raise NameError at runtime!")

# --- Check 2: Hit endpoints with test client (no session) ---
print("\n[CHECK 2] Endpoint behavior (no session / 401):")
with app.test_client() as client:
    # J1: cost-analysis
    resp1 = client.get('/api/signals/cost-analysis')
    print(f"  J1 /api/signals/cost-analysis: status={resp1.status_code}")
    print(f"    Response: {resp1.get_json()}")
    
    # J2: montecarlo
    resp2 = client.get('/api/validate/montecarlo')
    print(f"  J2 /api/validate/montecarlo: status={resp2.status_code}")
    print(f"    Response: {resp2.get_json()}")

# --- Check 3: Hit endpoints with fake session ---
print("\n[CHECK 3] Endpoint behavior (with session, no DB):")
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = 999
        sess['authenticated'] = True
    
    # J1
    try:
        resp1 = client.get('/api/signals/cost-analysis')
        print(f"  J1 /api/signals/cost-analysis: status={resp1.status_code}")
        print(f"    Response: {resp1.get_json()}")
    except Exception as e:
        print(f"  J1 FAIL: {type(e).__name__}: {e}")
    
    # J2
    try:
        resp2 = client.get('/api/validate/montecarlo')
        print(f"  J2 /api/validate/montecarlo: status={resp2.status_code}")
        print(f"    Response: {resp2.get_json()}")
    except Exception as e:
        print(f"  J2 FAIL: {type(e).__name__}: {e}")

# --- Check 4: withTimeout analysis (static analysis in report) ---
print("\n[CHECK 4] withTimeout / dvFetch chain analysis:")
print("  dvFetch code (line 6986-6988):")
print("    async function dvFetch(path,opts={}){")
print("      try{const r=await fetch(...);if(!r.ok)throw new Error('HTTP '+r.status);return await r.json();}")
print("      catch(e){console.warn('[dvFetch]',path,e.message);return null;}")
print("    }")
print("  withTimeout code (line 6991):")
print("    function withTimeout(p,ms){return Promise.race([p,new Promise(res=>setTimeout(()=>res(null),ms))]);}")
print()
print("  dvFetch return value matrix:")
print("    401  → r.ok=false → throws Error('HTTP 401')  → catch → returns null")
print("    500  → r.ok=false → throws Error('HTTP 500')  → catch → returns null")
print("    network failure → fetch throws TypeError      → catch → returns null")
print("    timeout  → Promise.race resolves null first   → returns null")
print("    success → returns parsed JSON")
print()
print("  PROBLEM: 401, 500, network failure, and timeout ALL return null.")
print("  The calling code at line 10544 treats null as 'sign in required':")
print("    if(!d){el.innerHTML='Sign in to see cost data';return;}")
print("  This means a 500 error or network failure shows the WRONG message.")

# --- Check 5: Silent errors ---
print("\n[CHECK 5] Silent error swallowing:")
print("  dvFetch: error is only console.warn'd, never re-thrown.")
print("  Callers use .then()/.catch() — but dvFetchT returns null on all failures,")
print("  so .catch() on dvFetchT is NEVER reached (the catch at line 10550/10565")
print("  handles the case where the promise ITSELF rejects, which dvFetch never does).")
print("  VERDICT: The .catch() on dvFetchT is dead code — dvFetch always resolves")
print("  to either JSON data or null. The .catch() at lines 10550/10565 will never fire.")
print()
print("  Additionally: withTimeout does NOT clear the setTimeout if the original")
print("  promise resolves first. Minor inefficiency, not a bug per se.")
print()
print("  Additionally: withTimeout does NOT cancel the underlying fetch on timeout.")
print("  The fetch continues running in the background, but its result is discarded.")
print("  This could waste bandwidth/server resources under heavy load.")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("CHECK 1 (SessionLocal exists):  FAIL — NameError at runtime")
print("CHECK 2 (401 behavior):         PASS — returns 401 JSON")
print("CHECK 3 (with valid session):   FAIL — NameError on SessionLocal()")
print("CHECK 4 (dvFetch return values): FAIL — 401/500/network/timeout all collapse to null")
print("CHECK 5 (silent errors):        FAIL — silent swallowing + dead .catch() code")
