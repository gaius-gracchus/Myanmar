# Myanmar corporate network visualization

This repository contains scripts necessary for generating interactive visualizations of the network structure of Myanmar corporations and businessmen.

The data used to make these networks was originally leaked by [DDoSecrets][ddosecrets].

The visualization was generated using the following steps:

0. After downloading the torrent from the DDoSecrets website (you don't need to download the 351 GB file `myco_pdfs.tar`, you only need `myco_details.tar.zst`), extract the JSON files for each company using the command

    ```
    tar -I zstd -xf myco_details.tar.zst -C myco_details
    ```

1. Extract node and edge information from the datasets provided by the leak--for both the corporation-aggregated network and the officer-aggregated network, convert to NetworkX graphs, and export as GEXF files. The file `scripts/create_networks.py` performs these actions.

2. Use the GEXF files to compute a graph layout using the open source [Gephi][gephi] graphing library, export GEXF files containing the computed locations of each node. I found that the most aesthetically pleasing results were obtained by:

    * using the *Force Atlas 2* layout algorithm
    * allowing the layout to equilibrate for a few minutes, before imposing the *Prevent Overlap* *Behavior Alternative*, and then waiting another few minutes for the layout to equilibrate.
    * running the "Modularity" community detection algorithm, with a resolution of 1.0.

3. Use the node locations from the second GEXF file to create a visualization using the [HoloViews][holoviews] package and the [Bokeh][bokeh] backend. The files `scripts/generate_corporation_visualization.py` and `scripts/generate_officer_visualization.py` performs these actions.

[ddosecrets]: https://ddosecrets.com/wiki/Myanmar_Financials
[holoviews]: http://holoviews.org/
[bokeh]: https://docs.bokeh.org/en/latest/
[gephi]: https://gephi.org/