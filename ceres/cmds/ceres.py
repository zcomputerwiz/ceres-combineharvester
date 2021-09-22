from ceres.cmds.ceres_init import ceres_init_cmd
from io import TextIOWrapper
from pathlib import Path
# from ceres.cmds.init_all import init_all
import click

from ceres import __version__
from ceres.cmds.configure import configure_cmd
from ceres.cmds.farm import farm_cmd
from ceres.cmds.init import init_cmd
from ceres.cmds.keys import keys_cmd
from ceres.cmds.netspace import netspace_cmd
from ceres.cmds.passphrase import passphrase_cmd
from ceres.cmds.plots import plots_cmd
from ceres.cmds.show import show_cmd
from ceres.cmds.start import start_cmd
from ceres.cmds.stop import stop_cmd
from ceres.cmds.wallet import wallet_cmd
from ceres.cmds.plotnft import plotnft_cmd
from ceres.util.default_root import DEFAULT_KEYS_ROOT_PATH, DEFAULT_ROOT_PATH
from ceres.util.keychain import set_keys_root_path, supports_keyring_passphrase
from ceres.util.ssl import check_ssl
from typing import Optional

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def monkey_patch_click() -> None:
    # this hacks around what seems to be an incompatibility between the python from `pyinstaller`
    # and `click`
    #
    # Not 100% sure on the details, but it seems that `click` performs a check on start-up
    # that `codecs.lookup(locale.getpreferredencoding()).name != 'ascii'`, and refuses to start
    # if it's not. The python that comes with `pyinstaller` fails this check.
    #
    # This will probably cause problems with the command-line tools that use parameters that
    # are not strict ascii. The real fix is likely with the `pyinstaller` python.

    import click.core

    click.core._verify_python3_env = lambda *args, **kwargs: 0  # type: ignore


@click.group(
    help=f"\n  Manage ceres blockchain infrastructure ({__version__})\n",
    epilog="Try 'ceres start node', 'ceres netspace -d 192', or 'ceres show -s'",
    context_settings=CONTEXT_SETTINGS,
)
@click.option("--root-path", default=DEFAULT_ROOT_PATH, help="Config file root", type=click.Path(), show_default=True)
@click.option(
    "--keys-root-path", default=DEFAULT_KEYS_ROOT_PATH, help="Keyring file root", type=click.Path(), show_default=True
)
@click.option("--passphrase-file", type=click.File("r"), help="File or descriptor to read the keyring passphase from")
@click.pass_context
def cli(
    ctx: click.Context,
    root_path: str,
    keys_root_path: Optional[str] = None,
    passphrase_file: Optional[TextIOWrapper] = None,
) -> None:
    from pathlib import Path

    ctx.ensure_object(dict)
    ctx.obj["root_path"] = Path(root_path)

    # keys_root_path and passphrase_file will be None if the passphrase options have been
    # scrubbed from the CLI options
    if keys_root_path is not None:
        set_keys_root_path(Path(keys_root_path))

    if passphrase_file is not None:
        from .passphrase_funcs import cache_passphrase, read_passphrase_from_file

        try:
            cache_passphrase(read_passphrase_from_file(passphrase_file))
        except Exception as e:
            print(f"Failed to read passphrase: {e}")

    check_ssl(Path(root_path))


if not supports_keyring_passphrase():
    from ceres.cmds.passphrase_funcs import remove_passphrase_options_from_cmd

    # TODO: Remove once keyring passphrase management is rolled out to all platforms
    remove_passphrase_options_from_cmd(cli)


@cli.command("version", short_help="Show ceres version")
def version_cmd() -> None:
    print(__version__)


@cli.command("run_daemon", short_help="Runs ceres daemon")
@click.option(
    "--wait-for-unlock",
    help="If the keyring is passphrase-protected, the daemon will wait for an unlock command before accessing keys",
    default=False,
    is_flag=True,
    hidden=True,  # --wait-for-unlock is only set when launched by ceres start <service>
)
@click.pass_context
def run_daemon_cmd(ctx: click.Context, wait_for_unlock: bool) -> None:
    import asyncio
    from ceres.daemon.server import async_run_daemon
    from ceres.util.keychain import Keychain

    wait_for_unlock = wait_for_unlock and Keychain.is_keyring_locked()
    asyncio.get_event_loop().run_until_complete(async_run_daemon(ctx.obj["root_path"], wait_for_unlock=wait_for_unlock))



# @cli.command("init_all")
# @click.pass_context
# def init_all_cmd(ctx:click.Context) -> None:
#     print("init all")
#     init_all()






cli.add_command(keys_cmd)
cli.add_command(plots_cmd)
cli.add_command(wallet_cmd)
cli.add_command(plotnft_cmd)
cli.add_command(configure_cmd)
# cli.add_command(init_cmd)
cli.add_command(ceres_init_cmd)
cli.add_command(show_cmd)
cli.add_command(start_cmd)
cli.add_command(stop_cmd)
cli.add_command(netspace_cmd)
cli.add_command(farm_cmd)

if supports_keyring_passphrase():
    cli.add_command(passphrase_cmd)


def main() -> None:
    monkey_patch_click()
    cli()  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
