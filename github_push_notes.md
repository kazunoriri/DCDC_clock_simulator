# GitHub Push Notes

このMacでは、GitHub CLI (`gh`) を使ってHTTPS経由の `git push` ができるように設定済み。

## 現在の想定設定

```text
origin  https://github.com/kazunoriri/DCDC_clock_simulator.git
```

GitHub CLIのGit操作プロトコル:

```text
https
```

## 初回セットアップ手順

別のMacなどで同じ状態にする場合は、以下を実行する。

```sh
brew install gh
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git remote set-url origin https://github.com/kazunoriri/DCDC_clock_simulator.git
```

`gh auth login` では、ブラウザでGitHubのデバイス認証を行う。

## 確認

```sh
gh auth status
git remote -v
git push origin main
```

正常なら、変更がない場合は次のように表示される。

```text
Everything up-to-date
```

## 以前の失敗内容

HTTPS認証未設定の状態では、次のエラーで `git push` が失敗した。

```text
fatal: could not read Username for 'https://github.com': Device not configured
```

この場合は `gh auth login` と `gh auth setup-git` を実行する。
