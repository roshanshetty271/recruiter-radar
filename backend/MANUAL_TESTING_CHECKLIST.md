# 🧪 Manual Testing Checklist for RecruiterRadar Fixes

This checklist complements the automated tests and helps verify that all implemented fixes work correctly in the real application.

## 🏁 Quick Start Testing Commands

```bash
# 1. Run automated tests first
cd backend
python test_comprehensive_fixes.py

# 2. Start backend
uvicorn app.main:app --reload

# 3. Start frontend (in another terminal)
cd ../frontend
npm run dev
```

---

## 📋 Phase A: Data Mapping & UI Fixes

### ✅ Backend Data Validation Tests

**Test 1: API Response Structure**
- [ ] Make API call: `POST /api/chat` with message "find developers"
- [ ] Verify response has `ai_message`, `candidates`, `remaining_messages`, `processing_time_ms`
- [ ] Check each candidate has: `id`, `name`, `title`, `location`, `experience_years`, `skills`
- [ ] Verify `skills` is always an array (even when backend sends string)

**Test 2: Safe Defaults Applied**
- [ ] Check candidates with missing data still render properly
- [ ] Verify "Unknown Role" appears for missing `title`
- [ ] Verify "Location not specified" appears for missing `location`
- [ ] Verify empty skills array doesn't crash UI

### ✅ Frontend UI Rendering Tests

**Test 3: Candidate Cards Display**
- [ ] Open browser to `http://localhost:3000`
- [ ] Search for "Python developers"
- [ ] Verify candidate cards render without errors
- [ ] Check that distance badge only shows when there's actual distance data
- [ ] Verify skills display as tags/chips
- [ ] Confirm experience shows as number + "years"

**Test 4: Empty States**
- [ ] Search for something that returns no results
- [ ] Verify appropriate empty state message
- [ ] Ensure no candidate grid appears when candidates.length = 0

---

## 🤖 Phase B: Assistant Intelligence Tests

### ✅ Dual Tool System Tests

**Test 5: Search vs Analysis Tool Usage**
- [ ] Send message: "find Python developers" 
- [ ] Verify it uses `search_candidates` tool (check logs)
- [ ] Verify candidate cards appear
- [ ] Send follow-up: "what skills do they have?"
- [ ] Verify it uses `summarise_candidates` tool (check logs)
- [ ] Verify analysis response without new search

**Test 6: Analysis Types**
After a search, test each analysis type:
- [ ] "what skills do they have?" → Skills distribution
- [ ] "where are they located?" → Location breakdown  
- [ ] "what experience levels?" → Experience distribution
- [ ] Verify each gives different analysis formats

**Test 7: Session Memory**
- [ ] Search: "find React developers"
- [ ] Ask: "how many years experience do they have?"
- [ ] Verify it analyzes the React developers (not new search)
- [ ] Open new browser tab (new session)
- [ ] Ask same question → should trigger new search (no cached results)

### ✅ Conversation Flow Tests

**Test 8: Natural Conversation**
- [ ] "show me software engineers"
- [ ] "which ones know AWS?"
- [ ] "what about their experience levels?"
- [ ] "any in San Francisco?"
- [ ] Verify each builds on previous without unnecessary re-searching

**Test 9: Mixed Queries**
- [ ] Search for candidates
- [ ] Ask about weather (off-topic)
- [ ] Ask about candidate skills (back on-topic)
- [ ] Verify assistant handles topic switches gracefully

---

## 🛡️ Phase C: Robustness Tests

### ✅ Error Handling Tests

**Test 10: Assistant Timeout Simulation**
```bash
# Temporarily break OpenAI API key to test fallback
export OPENAI_API_KEY="invalid_key"
uvicorn app.main:app --reload
```
- [ ] Send chat message
- [ ] Verify fallback search logic kicks in
- [ ] Verify user still gets candidate results  
- [ ] Check `source` field in response = "fallback"

**Test 11: Malformed Data Handling**
- [ ] Use API client to send malformed requests
- [ ] Verify graceful error responses
- [ ] Check that UI doesn't crash on bad responses

### ✅ Performance Tests

**Test 12: Response Speed**
- [ ] Measure time from search to results display
- [ ] Should be < 3 seconds for assistant responses
- [ ] Should be < 8 seconds maximum (fallback timeout)
- [ ] Check browser network tab for timing

**Test 13: Cache Performance**
- [ ] Same search twice → second should be faster
- [ ] Check logs for cache hit messages
- [ ] Clear cache, retry → should be slower first time

---

## 🧹 Phase D: Session Hygiene Tests

### ✅ Session Management Tests

**Test 14: Session Storage**
- [ ] Open DevTools → Application → Session Storage
- [ ] Verify `session_id` is stored in sessionStorage (not localStorage)
- [ ] Close tab, reopen → new session ID should be generated
- [ ] Refresh tab → same session ID should persist

**Test 15: Thread Cleanup**
```bash
# Check thread database
cd backend/app/data/assistant_storage
sqlite3 threads.db ".dump"
```
- [ ] Verify threads are created with proper timestamps
- [ ] Run cleanup manually: check backend logs
- [ ] Verify old threads are removed from database

**Test 16: Cache Cleanup**
- [ ] Search for candidates (populates cache)
- [ ] Check `assistant_service.last_search_results` has data
- [ ] Wait for cleanup cycle or trigger manually
- [ ] Verify old cache entries are cleared

### ✅ Background Process Tests

**Test 17: Periodic Cleanup**
- [ ] Start backend, let it run for 2+ hours
- [ ] Check logs for periodic cleanup messages
- [ ] Verify cleanup happens automatically every hour
- [ ] Check that cleanup doesn't interfere with active sessions

---

## 🔄 Integration Tests

### ✅ Complete User Journey Tests

**Test 18: New User Experience**
1. [ ] Open fresh browser (incognito/private mode)
2. [ ] Land on homepage
3. [ ] Search: "find senior developers"
4. [ ] View candidate cards
5. [ ] Ask: "which ones know Docker?"
6. [ ] View analysis results
7. [ ] Search for different role: "product managers"
8. [ ] Ask about their backgrounds
9. [ ] Close tab → verify session cleanup

**Test 19: Power User Experience**
1. [ ] Search multiple different queries
2. [ ] Mix search and analysis questions
3. [ ] Try edge cases (very specific searches)
4. [ ] Test with 10+ messages in session
5. [ ] Verify performance stays consistent

**Test 20: Error Recovery**
1. [ ] Start normal flow
2. [ ] Disconnect internet briefly
3. [ ] Reconnect and continue
4. [ ] Verify graceful recovery
5. [ ] Check that session state preserved

### ✅ Cross-Browser Tests

**Test 21: Browser Compatibility**
- [ ] Test in Chrome
- [ ] Test in Firefox  
- [ ] Test in Safari (if available)
- [ ] Test in Edge
- [ ] Verify session storage works in all

**Test 22: Mobile Responsiveness**
- [ ] Open on mobile device or simulate mobile
- [ ] Test search functionality
- [ ] Verify candidate cards display properly
- [ ] Test chat interface usability

---

## 📊 Monitoring & Verification

### ✅ Log Analysis

**Test 23: Backend Logs Review**
```bash
# Watch logs during testing
tail -f backend.log
```
- [ ] Verify no error messages during normal flow
- [ ] Check assistant vs fallback usage ratio
- [ ] Verify cache hit/miss logging
- [ ] Monitor API response times

**Test 24: Database State**
```bash
# Check assistant database
sqlite3 backend/app/data/assistant_storage/threads.db
.schema
SELECT * FROM threads;
```
- [ ] Verify thread records are clean
- [ ] Check timestamp accuracy
- [ ] Verify session_id format consistency

### ✅ Performance Monitoring

**Test 25: Resource Usage**
- [ ] Monitor CPU usage during heavy testing
- [ ] Check memory usage over time
- [ ] Verify no memory leaks in long sessions
- [ ] Monitor database size growth

---

## 🚨 Red Flag Indicators

Watch out for these issues that indicate problems:

### Backend Issues
- [ ] 🚨 Response times > 8 seconds
- [ ] 🚨 Assistant fallback rate > 20%
- [ ] 🚨 Errors in cleanup process
- [ ] 🚨 Database connection errors
- [ ] 🚨 OpenAI API quota exceeded

### Frontend Issues  
- [ ] 🚨 UI crashes on candidate display
- [ ] 🚨 Infinite loading states
- [ ] 🚨 Console errors on search
- [ ] 🚨 Session storage not working
- [ ] 🚨 Chat messages not appearing

### Data Issues
- [ ] 🚨 Candidates missing required fields
- [ ] 🚨 Skills showing as strings instead of arrays
- [ ] 🚨 Match scores outside 0-1 range
- [ ] 🚨 Analysis returning no data
- [ ] 🚨 Cache not preventing duplicate searches

---

## ✅ Final Verification Checklist

After completing all tests:

- [ ] All automated tests pass (>80% success rate)
- [ ] No red flag indicators present
- [ ] Search → analysis flow works smoothly
- [ ] Fallback system activates when needed
- [ ] Sessions clean up properly
- [ ] UI renders candidate cards correctly
- [ ] Performance is acceptable (<3s typical, <8s max)
- [ ] Error states are user-friendly
- [ ] Cross-browser compatibility confirmed

## 📝 Test Results Documentation

Document your findings:

```markdown
## Test Session Results
Date: [DATE]
Tester: [NAME]

### Automated Test Results
- Tests Run: X
- Passed: Y
- Failed: Z
- Success Rate: N%

### Manual Test Summary
- Phase A (Data/UI): ✅/❌
- Phase B (Assistant): ✅/❌  
- Phase C (Robustness): ✅/❌
- Phase D (Session): ✅/❌

### Issues Found
1. [Issue description]
2. [Issue description]

### Performance Notes
- Average response time: Xs
- Fallback rate: Y%
- Cache hit rate: Z%
```

---

**Remember**: This manual testing checklist should be used alongside the automated tests. The combination gives you confidence that all the major fixes are working correctly in real-world scenarios! 🎯 