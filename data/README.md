# data ディレクトリの扱い
- `data/raw`: TalkBank (Nadig) など **外部配布NG/大容量**のデータは含めません。取得元: https://talkbank.org/asd/access/English/Nadig.html
- `data/processed`: スクリプトで再生成できる中間物。原則としてリポジトリには含めません（.gitignore で除外）。必要な最終アウトプットは `docs/` にHTMLとして公開します。
