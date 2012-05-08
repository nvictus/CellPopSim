classdef HdfLineage
    %HDFLINEAGE Extract single-cell timeseries data from PyCps simulation file.
    %   For hdf5 files created using save_lineage routine. Creating an
    %   instance without specifying a file name will open a dialog window.
    
    properties
        Filename
        NumAgents
        Time
        Data
    end
    
    properties (Hidden)
        state_names
        adjacency_list
        start_row
        num_events
    end
    
    methods
        function self = HdfLineage(filename)
            %HDFLINEAGE Constructor
            %   filename - name of hdf file 
            
            if nargin == 0
                filename = uigetfile('*.hdf5');
            end
            
            self.Filename = filename;
            
            self.state_names = self.getVarNames('state_info');
            adj_info = hdf5read(filename, 'adj_data')';
            self.NumAgents = size(adj_info, 1);
            self.adjacency_list = adj_info(:,1:2);
            self.start_row = adj_info(:,3);
            self.num_events = adj_info(:,4);            
            self.Time = hdf5read(filename, 'time');
            self.Data = hdf5read(filename, 'state_data')'; 
        end
        
        function [time, data] = get(self, var_name, agent_index)
            % GET Pull out time series data for a particular cell's lifetime
            if (agent_index < 1 || agent_index > self.NumAgents )
                error('Index out of range');
            end
            
            % Find appropriate column in the data matrix
            col = find(strcmp(self.state_names, var_name));
            if isempty(col)
                error('Invalid variable name');
            end
            
            % Node info in hdf file assumes 0-based indexing on the data 
            % matrix so we convert row ranges to 1-based format to avoid 
            % off-by-one errors
            start = self.start_row(agent_index) + 1;
            stop = start + self.num_events(agent_index) - 1;
            
            time = self.Time(start:stop);
            data = self.Data(start:stop, col);
        end
        
        function display(self)            
            disp(self);
            disp('  Dataset Variables:');
            for i = 1:length(self.state_names)
                fprintf('\t\t%s\n', self.state_names{i});
            end
        end
    end
    
    methods (Access = private)
       function names = getVarNames(self, group_name)
            fid = H5F.open(self.Filename,'H5F_ACC_RDONLY','H5P_DEFAULT');
            dset_id = H5D.open(fid, group_name);
            names = cellstr(...
                            H5D.read(dset_id,...
                                     'H5ML_DEFAULT',...
                                     'H5S_ALL',...
                                     'H5S_ALL',...
                                     'H5P_DEFAULT')' );
            H5D.close(dset_id)
            H5F.close(fid)
        end 
    end
    
end

