# AWS Cost Watcher Security & Bug Review

## Security Issues Found

### 🔴 HIGH: Webhook URL Validation Missing
**Problem:** No validation on webhook URLs in config
- Users can enter arbitrary URLs (file://, ftp://, etc.)
- Potential SSRF attacks against internal services
- No URL scheme restrictions

**Fix:**
```python
def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL is safe."""
    if not url:
        return True
    parsed = urllib.parse.urlparse(url)
    allowed_schemes = {'http', 'https'}
    return parsed.scheme in allowed_schemes and parsed.netloc
```

### 🔴 HIGH: YAML Safe Loading (GOOD)
**Status:** ✅ Already using `yaml.safe_load()` - this is correct!
- Prevents arbitrary code execution via YAML deserialization

### 🔴 HIGH: Exception Information Disclosure
**Problem:** Raw AWS exceptions exposed to user
```python
click.echo(f"❌ AWS Error: {e}", err=True)  # Line 103, 472, etc.
```
**Risk:** May leak internal AWS account info, IAM details
**Fix:** Sanitize exception messages, log full details separately

### 🟡 MEDIUM: Input Validation
**Issues:**
1. **Float conversion without bounds checking**
   ```python
   config["budget"] = float(os.environ.get("AWS_COST_BUDGET"))  # Line 59
   ```
   - Can cause overflow/underflow
   - No range validation (negative budgets?)

2. **No AWS region validation**
   - Users can enter invalid regions
   - AWS SDK might fail unexpectedly

### 🟡 MEDIUM: HTTP Request Security
**Issues:**
1. **No User-Agent header** - some services block requests without UA
2. **No request size limits** - webhook responses unbounded
3. **Timeout only 10s** - might be too short for some webhooks

### 🟡 MEDIUM: File Path Security
**Problem:** Config file paths not sanitized
```python
for config_file in DEFAULT_CONFIG_FILES:  # Line 46
```
**Risk:** Path traversal if user controls config paths (low likelihood)

## Bugs Found

### 🔴 HIGH: Month Calculation Bug
**Problem:** Inconsistent month boundary calculations
```python
# forecast command - line 520
next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)

# history command - line 565  
start_date = (today.replace(day=1) - timedelta(days=months*31))
```
**Issues:**
- `months*31` is inaccurate (not all months have 31 days)
- February edge cases not handled properly
- Forecast calculation is overly complex

**Fix:** Use `dateutil.relativedelta` or proper month arithmetic

### 🔴 HIGH: Division by Zero
**Problem:** Multiple places with potential division by zero
```python
avg_daily = total_so_far / days_elapsed if days_elapsed > 0 else 0  # Line 533
pct = (forecast_total / budget * 100) if budget > 0 else 0  # Line 545
```
**Status:** ✅ Actually protected with conditionals - good!

### 🟡 MEDIUM: Type Safety
**Issues:**
1. **Missing None checks on API responses**
   ```python
   amount = float(result["Total"]["UnblendedCost"]["Amount"])  # Line 126, 351
   ```
   - AWS API could return None/null values
   
2. **Inconsistent return types**
   - Some functions return dict, others return specific types
   - No type hints on return values

### 🟡 MEDIUM: Error Handling Gaps
**Issues:**
1. **Network timeouts not handled properly**
2. **Partial API failures not handled** (what if only some months return data?)
3. **Rate limiting not considered** (AWS has API limits)

## Recommended Fixes (Priority Order)

### Immediate (Security)
1. **Add webhook URL validation**
2. **Sanitize exception messages**
3. **Add input bounds checking for budget values**

### Soon (Bugs)  
1. **Fix month calculation with proper date library**
2. **Add None checks for AWS API responses**
3. **Add retry logic with exponential backoff**

### Later (Quality)
1. **Add comprehensive type hints**
2. **Implement request size limits**
3. **Add AWS region validation**
4. **Improve error messages**

## Code Quality Issues

### Missing Features for Production
- No logging (only print statements)
- No rate limiting for API calls
- No retry logic for failed requests
- No configuration validation schema
- No integration tests with real AWS API

### Emoji Issue
- 17 different emojis hardcoded throughout
- No accessibility considerations (screen readers)
- No terminal compatibility checks

## Conclusion

**Overall Assessment:** Code is functional but needs security hardening before production use.

**Critical Path:**
1. Fix webhook URL validation (security)
2. Sanitize error messages (security) 
3. Fix date calculations (reliability)
4. Add proper input validation (robustness)

The emoji issue is cosmetic compared to these security/reliability concerns.