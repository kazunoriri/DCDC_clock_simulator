# GitHub Push Notes

このリポジトリでは、HTTPS経由の `git push` が次のエラーで失敗する場合がある。

```text
fatal: could not read Username for 'https://github.com': Device not configured
```

その場合はSSH認証を使う。

## 確認

```sh
ssh -T git@github.com
```

成功時の例:

```text
Hi kazunoriri! You've successfully authenticated, but GitHub does not provide shell access.
```

## originをSSH URLにする

```sh
git remote set-url origin git@github.com:kazunoriri/DCDC_clock_simulator.git
```

## プッシュ

```sh
git push origin main
```

現在の想定リモート:

```text
origin  git@github.com:kazunoriri/DCDC_clock_simulator.git
```
