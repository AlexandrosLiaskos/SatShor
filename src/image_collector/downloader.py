import logging
import os
import zipfile

import requests
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
)

console = Console()
logger = logging.getLogger(__name__)
ODATA_DOWNLOAD_BASE_URL = "https://download.dataspace.copernicus.eu/odata/v1"


def list_product_nodes(
    product_id: str, access_token: str, node_path: str = ""
) -> list | None:
    if not product_id or not access_token:
        logger.error("Product ID and Access Token are required to list nodes.")
        return None
    headers = {"Authorization": f"Bearer {access_token}"}
    if node_path:
        nodes_url = f"{ODATA_DOWNLOAD_BASE_URL}/Products({product_id})/Nodes('{node_path}')/Nodes"
    else:
        nodes_url = f"{ODATA_DOWNLOAD_BASE_URL}/Products({product_id})/Nodes"
    logger.info(f"Listing nodes for product {product_id} at path '{node_path or '/'}'.")
    logger.debug(f"Node listing URL: {nodes_url}")
    try:
        response = requests.get(nodes_url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        nodes = data.get("value", data.get("result", []))
        logger.info(f"Found {len(nodes)} nodes at path '{node_path or '/'}'.")
        return nodes if isinstance(nodes, list) else []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(
                f"Node path '{node_path}' not found or is a file (404). Product: {product_id}"
            )
            return []
        else:
            logger.error(
                f"HTTP Error listing nodes for product {product_id} at path '{node_path or '/'}': {e}"
            )
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text[:500]}...")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Network/Request Error listing nodes for product {product_id} at path '{node_path or '/'}': {e}"
        )
        return None
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while listing nodes for product {product_id}: {e}"
        )
        return None


def download_product(
    product_id: str,
    product_name: str,
    access_token: str,
    output_dir: str = ".",
    node_path: str | None = None,
):
    if not product_id or not access_token:
        logger.error("Product ID and Access Token are required for download.")
        return
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    download_url = f"{ODATA_DOWNLOAD_BASE_URL}/Products({product_id})/$value"
    output_filename = f"{product_name}.zip"
    output_path = os.path.join(output_dir, output_filename)
    extract_path = os.path.splitext(output_path)[0]
    if node_path:
        console.print(
            "[yellow]Warning: Node-specific download logic currently disabled in this modification.[/]"
        )
        logger.warning(
            "Node path provided but logic focuses on full zip download/unzip."
        )
        download_target_description = f"node '{node_path}' from product {product_name}"
        node_path = None
    else:
        download_target_description = f"full product {product_name}"
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Checking for product: {product_name}")
    logger.info(f"Expected Zip Path: {output_path}")
    logger.info(f"Expected Extract Path: {extract_path}")
    if os.path.isdir(extract_path):
        console.print(
            f":white_check_mark: [green]Product '{os.path.basename(extract_path)}' already extracted. Skipping.[/]"
        )
        return
    if os.path.exists(output_path):
        console.print(
            f":file_folder: Found existing archive [cyan]'{os.path.basename(output_path)}'[/]. Attempting to unzip..."
        )
        if _unzip_and_remove(output_path, extract_path):
            return
        else:
            console.print(
                ":warning: [yellow]Failed to unzip existing archive. Will download a fresh copy.[/]"
            )
            _cleanup_incomplete_file(output_path)
    logger.info(f"Proceeding to download: {download_target_description}")
    try:
        console.print(
            f":arrow_down: Downloading [cyan]{os.path.basename(output_path)}[/]..."
        )
        with requests.get(
            download_url,
            headers=headers,
            stream=True,
            allow_redirects=True,
            timeout=120,
        ) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            block_size = 8192
            progress = Progress(
                TextColumn("[bold blue]{task.description}", justify="right"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.1f}%",
                "•",
                TransferSpeedColumn(),
                "•",
                TimeElapsedColumn(),
            )
            task_id = progress.add_task(
                f"Downloading {os.path.basename(output_path)}...", total=total_size
            )
            with progress:
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            progress.update(task_id, advance=len(chunk))
            final_size = os.path.getsize(output_path)
            if final_size != total_size and total_size != 0:
                console.print(
                    f":x: [bold red]Error: Final size ({final_size}) doesn't match expected ({total_size}). Download may be corrupt.[/]"
                )
            else:
                console.print(
                    f":white_check_mark: [bold green]Successfully downloaded '{os.path.basename(output_path)}'[/]"
                )
                _unzip_and_remove(output_path, extract_path)
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error downloading {download_target_description}: {e}")
        console.print(
            f":x: [bold red]HTTP Error downloading '{os.path.basename(output_path)}'. Status: {e.response.status_code}. Check logs.[/]"
        )
        _cleanup_incomplete_file(output_path)
    except requests.exceptions.RequestException as e:
        logger.error(
            f"Network/Request Error downloading {download_target_description}: {e}"
        )
        console.print(
            f":x: [bold red]Network Error downloading '{os.path.basename(output_path)}'. Check connection and logs.[/]"
        )
        _cleanup_incomplete_file(output_path)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during download of {download_target_description}: {e}"
        )
        console.print(
            f":x: [bold red]Unexpected error during download of '{os.path.basename(output_path)}'. Check logs.[/]"
        )
        _cleanup_incomplete_file(output_path)


def _unzip_and_remove(zip_path: str, extract_dir: str) -> bool:
    if not zip_path.lower().endswith(".zip"):
        logger.warning(f"Attempted to unzip non-zip file: {zip_path}")
        return False
    console.print(
        f":open_file_folder: Extracting [cyan]{os.path.basename(zip_path)}[/] to [cyan]{os.path.basename(extract_dir)}[/]..."
    )
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            os.makedirs(extract_dir, exist_ok=True)
            zip_ref.extractall(extract_dir)
        console.print(":white_check_mark: [green]Extraction complete.[/]")
        try:
            os.remove(zip_path)
            console.print(
                f":wastebasket: [dim]Removed archive '{os.path.basename(zip_path)}'.[/]"
            )
            return True
        except OSError as e:
            logger.error(f"Failed to remove zip archive {zip_path}: {e}")
            console.print(
                f":warning: [yellow]Could not remove zip archive '{os.path.basename(zip_path)}'.[/]"
            )
            return True
    except zipfile.BadZipFile:
        logger.error(f"Failed to unzip {zip_path}: Bad zip file.")
        console.print(
            f":x: [red]Error: Could not unzip '{os.path.basename(zip_path)}'. File may be corrupt.[/]"
        )
        return False
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during unzipping of {zip_path}: {e}"
        )
        console.print(
            f":x: [red]Error: An unexpected error occurred during unzipping '{os.path.basename(zip_path)}'.[/]"
        )
        return False


def _cleanup_incomplete_file(file_path: str):
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Removed incomplete/corrupt file: {file_path}")
        except OSError as oe:
            logger.error(f"Failed to remove incomplete/corrupt file {file_path}: {oe}")


def _download_file_with_progress(
    url, headers, output_path, description, total_size=None
):
    response = requests.get(url, headers=headers, stream=True, allow_redirects=True)
    response.raise_for_status()
    if total_size is None:
        total_size = int(response.headers.get("content-length", 0))
    block_size = 8192
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "|",
        TransferSpeedColumn(),
        "|",
        TimeElapsedColumn(),
    ) as progress:
        task_id = progress.add_task(description, total=total_size)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(block_size):
                if chunk:
                    f.write(chunk)
                    progress.update(task_id, advance=len(chunk))
    if total_size != 0 and not progress.tasks[task_id].finished:
        print(
            f"[Warning] Download of {description} finished, but progress bar did not complete."
        )


if __name__ == "__main__":
    print("Downloader module. Run collector.py to use.")
