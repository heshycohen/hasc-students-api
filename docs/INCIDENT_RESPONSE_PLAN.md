# Incident Response Plan

## 1. Incident classification

| Severity | Description | Examples |
|----------|-------------|----------|
| **Critical** | Data breach, unauthorized access to PHI/PII | Stolen credentials, exposed student records |
| **High** | System compromise, repeated failed access | Brute force, malware |
| **Medium** | Suspicious activity, config errors | Unusual export volume, misconfiguration |
| **Low** | Minor security events | Single failed login, expired cert warning |

---

## 2. Response procedures

### Step 1: Detection
- Monitor security events and compliance dashboard.
- Review access and audit logs regularly (daily recommended).
- Rely on automated alerts for critical/high severity.

### Step 2: Containment
- Isolate affected systems where possible.
- Disable compromised accounts and rotate credentials.
- Preserve evidence (logs, timestamps) before changes.

### Step 3: Investigation
- Review access and audit logs for scope and impact.
- Identify what data was accessed or exfiltrated.
- Document findings and timeline.

### Step 4: Notification
- **Internal:** Notify designated security/management contact within 1 hour of confirmation.
- **Affected individuals:** Per HIPAA, notify within 60 days; best practice sooner (e.g. within 72 hours for significant breaches).
- **HHS:** Report to HHS if breach affects 500+ individuals (see [HHS Breach Notification](https://www.hhs.gov/hipaa/for-professionals/breach-notification/index.html)).
- **FERPA:** Follow district/school policy and applicable state laws for education records.

### Step 5: Recovery
- Restore from known-good backups if needed.
- Patch vulnerabilities and harden configurations.
- Re-enable access only after verification.

### Step 6: Post-incident
- Conduct post-mortem and update this plan.
- Update procedures and training as needed.

---

## 3. Contact information

| Role | Contact |
|------|---------|
| Security / IT lead | _[Fill in]_ |
| Legal / compliance | _[Fill in]_ |
| Management / decision maker | _[Fill in]_ |
| HHS breach reporting | https://ocrportal.hhs.gov/ocr/breach/wizard_breach.jsf |

---

## 4. Breach notification template (outline)

- Date of discovery and date of incident (if known).
- Description of the incident and types of PHI/PII involved.
- Steps individuals should take to protect themselves.
- What the organization is doing in response.
- Contact for questions.

---

*Review and update this plan at least annually. See COMPLETION_GUIDE.md §9 for more detail.*
