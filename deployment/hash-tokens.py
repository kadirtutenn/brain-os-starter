import hashlib
import os
import shutil
import sys
import time


def main() -> None:
    src, dst, uid, gid = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    entries = []
    for line in open(src).read().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) != 3:
            continue
        token, user, role = (p.strip() for p in parts)
        digest = (
            token
            if token.startswith("sha256$")
            else "sha256$" + hashlib.sha256(token.encode("utf-8")).hexdigest()
        )
        entries.append(digest + ":" + user + ":" + role)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if os.path.exists(dst):
        shutil.copy(dst, dst + ".pre-migrate-" + stamp)
    open(dst, "w").write("\n".join(entries) + "\n")
    os.chown(dst, uid, gid)
    os.chmod(dst, 0o600)
    print("migrate_tokens:", len(entries), "kullanici hash-lendi")


if __name__ == "__main__":
    main()
